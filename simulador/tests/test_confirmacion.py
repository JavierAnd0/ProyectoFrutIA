import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from confirmacion import CONFIRMADA, ESPERANDO, REGISTRADA, Confirmador  # noqa: E402


def ver(c, etiqueta, veces, conf=0.9, presencia=True):
    for _ in range(veces):
        estado = c.procesar(etiqueta, conf, presencia)
    return estado


def test_confirma_tras_n_fotogramas_seguidos():
    c = Confirmador(frames_confirmar=5)
    assert ver(c, "pera", 4) == ESPERANDO
    assert ver(c, "pera", 1) == CONFIRMADA
    assert c.fruta == "pera" and c.confianza == 0.9


def test_baja_confianza_o_fondo_reinicia_la_cuenta():
    c = Confirmador(frames_confirmar=3, umbral=0.75)
    ver(c, "kiwi", 2)
    c.procesar("kiwi", 0.5)            # baja confianza: se pierde la racha
    assert ver(c, "kiwi", 2) == ESPERANDO
    c.procesar("fondo", 0.99)
    assert ver(c, "kiwi", 2) == ESPERANDO
    assert ver(c, "kiwi", 1) == CONFIRMADA


def test_predicciones_alternadas_no_confirman():
    c = Confirmador(frames_confirmar=3)
    for _ in range(10):
        c.procesar("pera", 0.9)
        c.procesar("kiwi", 0.9)
    assert c.estado == ESPERANDO


def test_sin_presencia_no_confirma():
    c = Confirmador(frames_confirmar=3)
    assert ver(c, "banano", 10, presencia=False) == ESPERANDO


def test_boton_sin_fruta_se_ignora():
    c = Confirmador()
    assert c.boton("entrada") is None
    assert "no hay una fruta" in c.mensaje


def test_un_solo_movimiento_aunque_se_pulse_varias_veces():
    c = Confirmador(frames_confirmar=3)
    ver(c, "banano", 3)
    mov = c.boton("salida")
    assert (mov.fruta, mov.tipo) == ("banano", "salida")
    assert c.estado == REGISTRADA
    # la fruta sigue delante de la cámara y se vuelve a pulsar
    ver(c, "banano", 20)
    assert c.boton("salida") is None
    assert c.boton("entrada") is None


def test_retirar_la_fruta_rearma_para_el_siguiente_registro():
    c = Confirmador(frames_confirmar=3, frames_retiro=4)
    ver(c, "pera", 3)
    assert c.boton("entrada") is not None
    ver(c, "fondo", 3)
    assert c.estado == REGISTRADA        # todavía no cuenta como retirada
    ver(c, "fondo", 1)
    assert c.estado == ESPERANDO
    ver(c, "pera", 3)
    assert c.boton("entrada") is not None


def test_un_parpadeo_de_fondo_no_cuenta_como_retiro():
    c = Confirmador(frames_confirmar=3, frames_retiro=4)
    ver(c, "pera", 3)
    c.boton("entrada")
    ver(c, "fondo", 2)
    ver(c, "pera", 1)                    # vuelve a verse: se reinicia el contador
    ver(c, "fondo", 3)
    assert c.estado == REGISTRADA


def test_clases_de_manzana_se_registran_como_manzana():
    c = Confirmador(frames_confirmar=4)
    for etiqueta in ["manzana_roja", "manzana_verde", "manzana_roja", "manzana_verde"]:
        c.procesar(etiqueta, 0.9)
    assert c.estado == CONFIRMADA and c.fruta == "manzana"
    assert c.boton("entrada").fruta == "manzana"


def test_cambiar_de_fruta_sin_pasar_por_fondo():
    c = Confirmador(frames_confirmar=3)
    ver(c, "pera", 3)
    ver(c, "kiwi", 3)
    assert c.estado == CONFIRMADA and c.fruta == "kiwi"


def test_confianza_es_la_media_de_los_fotogramas_que_confirmaron():
    c = Confirmador(frames_confirmar=3)
    for conf in (0.8, 0.9, 1.0):
        c.procesar("kiwi", conf)
    assert c.confianza == 0.9
