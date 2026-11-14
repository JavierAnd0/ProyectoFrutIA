import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from inventario import Inventario  # noqa: E402
from servicio import Servicio  # noqa: E402

BOG = ZoneInfo("America/Bogota")
FRUTAS = ["manzana", "pera", "banano", "kiwi"]


@pytest.fixture
def inv():
    return Inventario(":memory:", FRUTAS)


def test_stock_inicial_en_cero(inv):
    assert inv.stock() == {f: 0 for f in FRUTAS}


def test_entrada_y_salida(inv):
    assert inv.registrar_movimiento("manzana", "entrada", 3).ok
    assert inv.registrar_movimiento("manzana", "salida", 1).ok
    assert inv.stock()["manzana"] == 2


def test_salida_con_stock_cero_se_rechaza_y_no_se_guarda(inv):
    r = inv.registrar_movimiento("banano", "salida")
    assert not r.ok and r.aviso == "Salida de banano rechazada: stock 0"
    assert inv.stock()["banano"] == 0


def test_salida_mayor_al_stock_se_rechaza(inv):
    inv.registrar_movimiento("kiwi", "entrada", 1)
    assert not inv.registrar_movimiento("kiwi", "salida", 2).ok
    assert inv.stock()["kiwi"] == 1


@pytest.mark.parametrize("fruta,tipo,cantidad,confianza", [
    ("sandia", "entrada", 1, None),     # fruta desconocida
    ("manzana", "compra", 1, None),     # tipo inválido
    ("manzana", "entrada", 0, None),    # cantidad 0
    ("manzana", "entrada", "2", None),  # cantidad no entera
    ("manzana", "entrada", 1, 1.5),     # confianza fuera de rango
    (None, "entrada", 1, None),         # sin fruta
])
def test_movimientos_invalidos(inv, fruta, tipo, cantidad, confianza):
    r = inv.registrar_movimiento(fruta, tipo, cantidad, confianza)
    assert not r.ok and r.aviso
    assert sum(inv.stock().values()) == 0


def test_mayusculas_y_espacios_se_normalizan(inv):
    assert inv.registrar_movimiento("  Manzana ", "entrada").ok
    assert inv.stock()["manzana"] == 1


def test_evento_repetido_no_se_cuenta_dos_veces(inv):
    assert inv.registrar_movimiento("pera", "entrada", evento_id="abc").ok
    r = inv.registrar_movimiento("pera", "entrada", evento_id="abc")
    assert r.duplicado and not r.ok
    assert inv.stock()["pera"] == 1


def test_resumen_hoy_y_semana(inv):
    ahora = datetime(2026, 11, 6, 15, 0, tzinfo=BOG)          # viernes
    inv.registrar_movimiento("banano", "entrada", 10, fecha=ahora - timedelta(days=10))
    inv.registrar_movimiento("banano", "salida", 1, fecha=ahora - timedelta(days=7))   # semana pasada
    inv.registrar_movimiento("banano", "salida", 2, fecha=datetime(2026, 11, 2, 8, 0, tzinfo=BOG))  # lunes
    inv.registrar_movimiento("banano", "salida", 3, fecha=ahora - timedelta(hours=2))  # hoy
    assert inv.resumen("banano", ahora) == {"salidas_hoy": 3, "salidas_semana": 5}


def test_resumen_compara_bien_fechas_en_utc(inv):
    # 23:30 en Bogotá del día anterior = 04:30 UTC de "hoy": no debe contar como hoy.
    ahora = datetime(2026, 11, 6, 12, 0, tzinfo=BOG)
    inv.registrar_movimiento("kiwi", "entrada", 5, fecha=ahora - timedelta(days=3))
    inv.registrar_movimiento("kiwi", "salida", 1,
                             fecha=datetime(2026, 11, 6, 4, 30, tzinfo=ZoneInfo("UTC")))
    assert inv.resumen("kiwi", ahora)["salidas_hoy"] == 0


def test_ambiente(inv):
    assert inv.registrar_ambiente(24.5, 60)
    assert not inv.registrar_ambiente("caliente", 60)
    assert not inv.registrar_ambiente(None, None)


def test_persistencia_en_archivo(tmp_path):
    ruta = str(tmp_path / "fruitai.db")
    Inventario(ruta, FRUTAS).registrar_movimiento("manzana", "entrada", 4)
    assert Inventario(ruta, FRUTAS).stock()["manzana"] == 4   # "al arrancar recalcula desde la BD"


# ---------- Servicio (sin broker) ----------
@pytest.fixture
def srv(inv):
    publicados = []
    s = Servicio(inv, lambda t, p, r: publicados.append((t, p, r)))
    s.publicados = publicados
    return s


def test_servicio_publica_stock_y_resumen(srv):
    srv.manejar("fruitai/movimiento", json.dumps({"fruta": "manzana", "tipo": "entrada", "cantidad": 2}).encode())
    pub = {t: (p, r) for t, p, r in srv.publicados}
    assert pub["fruitai/stock/manzana"] == ("2", True)
    assert pub["fruitai/resumen/manzana/salidas_hoy"] == ("0", True)


def test_servicio_avisa_salida_rechazada(srv):
    srv.manejar("fruitai/movimiento", b'{"fruta": "banano", "tipo": "salida"}')
    assert srv.publicados == [("fruitai/aviso", "Salida de banano rechazada: stock 0", False)]


def test_servicio_sobrevive_json_malo(srv):
    srv.manejar("fruitai/movimiento", b"esto no es json")
    srv.manejar("fruitai/ambiente", b"\xff\xfe")
    assert srv.publicados[0][0] == "fruitai/aviso"


def test_discovery_crea_sensores_en_espanol(srv):
    srv.publicar_discovery()
    nombres = {json.loads(p)["name"] for t, p, _ in srv.publicados}
    assert {"Stock manzana", "Salidas semana kiwi", "Temperatura frutero", "ESP32 conectado",
            "Fruta detectada", "Registrar entrada", "Registrar salida", "Cámara"} <= nombres
    assert all(r for _, _, r in srv.publicados)  # discovery siempre con retain
    boton = next(json.loads(p) for t, p, _ in srv.publicados if t.endswith("fruitai_registrar_entrada/config"))
    assert boton["command_topic"] == "fruitai/esp32/boton" and boton["payload_press"] == "entrada"
    assert boton["availability_topic"] == "fruitai/esp32/estado"   # deshabilitado si el ESP32 no está
