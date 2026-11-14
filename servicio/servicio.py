"""Servicio FruitAI: MQTT → SQLite → stock y resúmenes publicados a Home Assistant.

Es el único componente que escribe en la base de datos y el único que calcula
el stock (plan v4). Al conectarse recalcula y publica todo desde la BD.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import threading
from typing import Callable

import paho.mqtt.client as mqtt

from inventario import Inventario

P = "fruitai"
T_MOVIMIENTO = f"{P}/movimiento"
T_AMBIENTE = f"{P}/ambiente"
T_AVISO = f"{P}/aviso"
T_ESTADO = f"{P}/servicio/estado"
T_ESP32_ESTADO = f"{P}/esp32/estado"   # online/offline que publica el ESP32 (con LWT)
T_ESP32_DETECCION = f"{P}/esp32/deteccion"   # qué está viendo/confirmando el ESP32 (JSON, retain)
T_ESP32_BOTON = f"{P}/esp32/boton"           # HA → ESP32: "entrada" / "salida" (botones del panel)
T_ESP32_FOTO = f"{P}/esp32/foto"             # JPEG de la cámara (opcional), para verla en HA
T_HA_ESTADO = "homeassistant/status"

log = logging.getLogger("fruitai")

Publicar = Callable[[str, str, bool], None]  # (tópico, payload, retain)


class Servicio:
    """Lógica del servicio, independiente del cliente MQTT (testeable)."""

    def __init__(self, inventario: Inventario, publicar: Publicar):
        self.inv = inventario
        self.publicar = publicar

    # ---------- entrada ----------
    def manejar(self, topico: str, payload: bytes) -> None:
        try:
            if topico == T_MOVIMIENTO:
                self.manejar_movimiento(payload)
            elif topico == T_AMBIENTE:
                self.manejar_ambiente(payload)
            elif topico == T_HA_ESTADO and payload == b"online":
                log.info("Home Assistant reinició: republicando discovery y valores")
                self.publicar_discovery()
                self.publicar_todo()
        except Exception:  # un mensaje malo nunca debe tumbar el servicio
            log.exception("Error procesando %s: %r", topico, payload[:200])

    def manejar_movimiento(self, payload: bytes) -> None:
        datos = _json(payload)
        if not isinstance(datos, dict):
            self._avisar(f"Movimiento con formato inválido: {payload[:80]!r}")
            return
        r = self.inv.registrar_movimiento(
            datos.get("fruta"),
            datos.get("tipo"),
            datos.get("cantidad", 1),
            datos.get("confianza"),
            datos.get("evento_id"),
        )
        if r.duplicado:
            log.info("Evento repetido ignorado: %s", datos.get("evento_id"))
            return
        if not r.ok:
            self._avisar(r.aviso)
            return
        log.info("Movimiento guardado: %s", datos)
        self.publicar_fruta(r.fruta)

    def manejar_ambiente(self, payload: bytes) -> None:
        datos = _json(payload)
        if isinstance(datos, dict) and self.inv.registrar_ambiente(
            datos.get("temperatura"), datos.get("humedad")
        ):
            return
        log.warning("Lectura de ambiente inválida: %r", payload[:80])

    # ---------- salida ----------
    def publicar_fruta(self, fruta: str) -> None:
        stock = self.inv.stock()[fruta]
        self.publicar(f"{P}/stock/{fruta}", str(stock), True)
        for nombre, valor in self.inv.resumen(fruta).items():
            self.publicar(f"{P}/resumen/{fruta}/{nombre}", str(valor), True)

    def publicar_todo(self) -> None:
        for fruta in self.inv.frutas():
            self.publicar_fruta(fruta)

    def publicar_discovery(self) -> None:
        dispositivo = {
            "identifiers": ["fruitai"],
            "name": "FruitAI",
            "manufacturer": "Proyecto FruitAI",
            "model": "Servicio de inventario",
        }
        for fruta in self.inv.frutas():
            sensores = [
                ("stock", f"Stock {fruta}", f"{P}/stock/{fruta}", "mdi:fruit-watermelon"),
                ("salidas_hoy", f"Salidas hoy {fruta}", f"{P}/resumen/{fruta}/salidas_hoy", "mdi:export"),
                ("salidas_semana", f"Salidas semana {fruta}", f"{P}/resumen/{fruta}/salidas_semana", "mdi:calendar-week"),
            ]
            for clave, nombre, topico, icono in sensores:
                config = {
                    "name": nombre,
                    "unique_id": f"fruitai_{fruta}_{clave}",
                    "state_topic": topico,
                    "unit_of_measurement": "unidades",
                    "state_class": "measurement",
                    "icon": icono,
                    "availability_topic": T_ESTADO,
                    "device": dispositivo,
                }
                self.publicar(f"homeassistant/sensor/fruitai_{fruta}_{clave}/config", json.dumps(config), True)

        # Sensores de ambiente: los publica el ESP32, HA los lee directo de fruitai/ambiente.
        for clave, nombre, campo, clase, unidad in [
            ("temperatura", "Temperatura frutero", "temperatura", "temperature", "°C"),
            ("humedad", "Humedad frutero", "humedad", "humidity", "%"),
        ]:
            config = {
                "name": nombre,
                "unique_id": f"fruitai_ambiente_{clave}",
                "state_topic": T_AMBIENTE,
                "value_template": f"{{{{ value_json.{campo} }}}}",
                "device_class": clase,
                "unit_of_measurement": unidad,
                "state_class": "measurement",
                "device": dispositivo,
            }
            self.publicar(f"homeassistant/sensor/fruitai_ambiente_{clave}/config", json.dumps(config), True)

        # Conexión del ESP32: lo publica el propio ESP32 (online al conectar; el broker
        # publica offline por LWT si se desconecta sin avisar).
        config = {
            "name": "ESP32 conectado",
            "unique_id": "fruitai_esp32_conectado",
            "state_topic": T_ESP32_ESTADO,
            "payload_on": "online",
            "payload_off": "offline",
            "device_class": "connectivity",
            "device": dispositivo,
        }
        self.publicar("homeassistant/binary_sensor/fruitai_esp32_conectado/config", json.dumps(config), True)

        # Registro desde Home Assistant con la fruta que reconoció el ESP32. Los botones solo
        # mandan la orden: el ESP32 aplica la misma lógica anti-duplicados que con el botón
        # físico (registra solo con una fruta confirmada y una vez hasta que se retire).
        disponible = {"availability_topic": T_ESP32_ESTADO, "payload_available": "online",
                      "payload_not_available": "offline"}
        entidades = [
            ("sensor", "fruta_detectada", {
                "name": "Fruta detectada",
                "state_topic": T_ESP32_DETECCION,
                "value_template": "{{ value_json.fruta if value_json.estado != 'ESPERANDO' else 'ninguna' }}",
                "json_attributes_topic": T_ESP32_DETECCION,
                "icon": "mdi:eye",
            }),
            ("sensor", "estado_deteccion", {
                "name": "Estado detección",
                "state_topic": T_ESP32_DETECCION,
                "value_template": "{{ value_json.estado }}",
                "icon": "mdi:state-machine",
            }),
            ("button", "registrar_entrada", {
                "name": "Registrar entrada",
                "command_topic": T_ESP32_BOTON,
                "payload_press": "entrada",
                "icon": "mdi:plus-circle",
            }),
            ("button", "registrar_salida", {
                "name": "Registrar salida",
                "command_topic": T_ESP32_BOTON,
                "payload_press": "salida",
                "icon": "mdi:minus-circle",
            }),
            ("camera", "camara", {
                "name": "Cámara",
                "topic": T_ESP32_FOTO,
            }),
        ]
        for tipo, clave, extra in entidades:
            config = {"unique_id": f"fruitai_{clave}", "device": dispositivo, **disponible, **extra}
            self.publicar(f"homeassistant/{tipo}/fruitai_{clave}/config", json.dumps(config), True)

    def _avisar(self, texto: str | None) -> None:
        if texto:
            log.warning(texto)
            self.publicar(T_AVISO, texto, False)


def _json(payload: bytes):
    try:
        return json.loads(payload)
    except (ValueError, UnicodeDecodeError):
        return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    frutas = os.environ.get("FRUTAS", "manzana,pera,banano,kiwi").split(",")
    inv = Inventario(
        os.environ.get("DB_RUTA", "fruitai.db"), frutas, os.environ.get("TZ", "America/Bogota")
    )

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="fruitai-servicio")
    if os.environ.get("MQTT_USUARIO"):
        cliente.username_pw_set(os.environ["MQTT_USUARIO"], os.environ.get("MQTT_CLAVE"))
    cliente.will_set(T_ESTADO, "offline", qos=1, retain=True)

    def publicar(topico: str, payload: str, retain: bool) -> None:
        cliente.publish(topico, payload, qos=1, retain=retain)

    servicio = Servicio(inv, publicar)

    def on_connect(c, _u, _f, reason_code, _p):
        if reason_code.is_failure:
            log.error("No se pudo conectar al broker: %s", reason_code)
            return
        log.info("Conectado al broker")
        c.subscribe([(T_MOVIMIENTO, 1), (T_AMBIENTE, 1), (T_HA_ESTADO, 1)])
        publicar(T_ESTADO, "online", True)
        servicio.publicar_discovery()
        servicio.publicar_todo()

    def on_disconnect(_c, _u, _f, reason_code, _p):
        log.warning("Desconectado del broker (%s); reintentando…", reason_code)

    cliente.on_connect = on_connect
    cliente.on_disconnect = on_disconnect
    cliente.on_message = lambda _c, _u, msg: servicio.manejar(msg.topic, msg.payload)
    cliente.reconnect_delay_set(min_delay=1, max_delay=30)
    cliente.connect_async(os.environ.get("MQTT_HOST", "localhost"), int(os.environ.get("MQTT_PORT", "1883")))
    cliente.loop_start()

    # Republica los resúmenes cada minuto: "salidas hoy" debe volver a 0 a
    # medianoche aunque no llegue ningún evento.
    parar = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: parar.set())
    signal.signal(signal.SIGINT, lambda *_: parar.set())
    intervalo = int(os.environ.get("INTERVALO_RESUMEN", "60"))
    while not parar.wait(intervalo):
        if cliente.is_connected():
            servicio.publicar_todo()

    publicar(T_ESTADO, "offline", True)
    cliente.loop_stop()
    cliente.disconnect()


if __name__ == "__main__":
    main()
