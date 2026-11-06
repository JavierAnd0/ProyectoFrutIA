#!/usr/bin/env bash
# Crea mosquitto/config/passwd con los usuarios definidos en .env.
# Uso: ./scripts/crear_usuarios_mqtt.sh   (desde la raíz del proyecto)
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "Falta .env (copia .env.example)"; exit 1; }
set -a; source .env; set +a

docker compose run --rm --no-deps --entrypoint sh mosquitto -c "
  rm -f /mosquitto/config/passwd &&
  mosquitto_passwd -b -c /mosquitto/config/passwd '$MQTT_USUARIO_SERVICIO' '$MQTT_CLAVE_SERVICIO' &&
  mosquitto_passwd -b    /mosquitto/config/passwd '$MQTT_USUARIO_HA'       '$MQTT_CLAVE_HA' &&
  mosquitto_passwd -b    /mosquitto/config/passwd '$MQTT_USUARIO_ESP32'    '$MQTT_CLAVE_ESP32' &&
  chown mosquitto:mosquitto /mosquitto/config/passwd &&
  chmod 0700 /mosquitto/config/passwd"
echo "Usuarios MQTT creados. Reinicia el broker: docker compose restart mosquitto"
