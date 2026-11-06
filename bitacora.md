# Bitácora FruitAI

## Día 1 — jue 5 nov 2026
- Hice: [COMPLETAR]
- Problema / cómo lo resolví:
- Evidencia:

## Día 2 — vie 6 nov 2026
- Hice: repositorio Git con la estructura del Anexo A; docker-compose con Home Assistant, Mosquitto
  (usuario/clave por cliente) y el servicio Python; servicio MQTT → SQLite que calcula stock y
  resúmenes y los publica con MQTT discovery; simulador del ESP32; 20 pruebas automáticas.
  Flujo probado en el Mac: simulador → broker → SQLite → stock publicado con retain.
- Problema / cómo lo resolví: sin hardware (ni Pi ni ESP32). Se desarrolló en el Mac con Docker,
  que corre las mismas imágenes que usará la Pi. `network_mode: host` del plan no se comporta igual
  en Docker Desktop: se usan puertos publicados y nombres de servicio (`mosquitto`).
  Riesgo detectado: con MQTT QoS 1 un evento puede llegar dos veces → se añadió `evento_id`.
- Evidencia: [COMPLETAR: captura de `simular_esp32.py escuchar` y de la tabla movimientos]
