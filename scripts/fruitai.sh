#!/usr/bin/env bash
# Pruebas rápidas de FruitAI desde la terminal de la Raspberry Pi (o cualquier
# equipo donde corra el docker compose). No necesita Python ni paho instalados:
# usa mosquitto_pub/sub dentro del contenedor del broker.
#
#   ./scripts/fruitai.sh estado                 # contenedores y stock actual
#   ./scripts/fruitai.sh escuchar               # ver mensajes MQTT en vivo (Ctrl+C para salir)
#   ./scripts/fruitai.sh entrada manzana 3      # simula al ESP32: entran 3 manzanas
#   ./scripts/fruitai.sh salida pera            # sale 1 pera
#   ./scripts/fruitai.sh ambiente 24.5 60       # temperatura y humedad
#   ./scripts/fruitai.sh db                     # últimos registros en SQLite
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a

sub() { docker exec fruitai-mosquitto mosquitto_sub -u "$MQTT_USUARIO_HA" -P "$MQTT_CLAVE_HA" "$@"; }
pub() { docker exec fruitai-mosquitto mosquitto_pub -u "$MQTT_USUARIO_ESP32" -P "$MQTT_CLAVE_ESP32" -q 1 "$@"; }

case "${1:-}" in
  estado)
    docker ps --format "table {{.Names}}\t{{.Status}}"
    echo; echo "Stock (retenido en el broker):"
    sub -t 'fruitai/stock/#' -v -W 2 2>/dev/null || true ;;
  escuchar)
    echo "Escuchando fruitai/# (Ctrl+C para salir)…"
    sub -t 'fruitai/#' -v ;;
  entrada|salida)
    fruta="${2:?falta la fruta}"; n="${3:-1}"
    pub -t fruitai/movimiento -m "{\"fruta\":\"$fruta\",\"tipo\":\"$1\",\"cantidad\":$n,\"evento_id\":\"pi-$(date +%s%N)\"}"
    sleep 1
    sub -t "fruitai/stock/$fruta" -C 1 -v ;;
  ambiente)
    pub -r -t fruitai/ambiente -m "{\"temperatura\":${2:?falta temperatura},\"humedad\":${3:?falta humedad}}"
    echo "Enviado: ${2} °C, ${3} %" ;;
  db)
    docker exec fruitai-servicio python -c '
import sqlite3
c = sqlite3.connect("/data/fruitai.db")
print("Últimos movimientos (id, fruta_id, tipo, cantidad, confianza, fecha, evento_id):")
for r in c.execute("select * from movimientos order by id desc limit 5"): print(" ", r)
print("Últimas lecturas de ambiente:")
for r in c.execute("select * from lecturas_ambiente order by rowid desc limit 3"): print(" ", r)' ;;
  *)
    sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//' ;;
esac
