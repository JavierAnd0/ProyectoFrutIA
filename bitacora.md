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
  La automatización de avisos falló (`mqtt_not_setup_cannot_subscribe`) porque HA arrancó antes de
  configurar la integración MQTT; se resolvió reiniciando HA (o recargando automatizaciones) después
  de agregar MQTT. En una instalación nueva: primero MQTT, luego automatizaciones.
- Evidencia: [COMPLETAR: captura de `simular_esp32.py escuchar` y de la tabla movimientos]

## Día 3 — sáb 7 nov 2026
- Hice: oraciones locales de Assist en español (`homeassistant/custom_sentences/es/fruitai.yaml`)
  para stock, salidas de hoy y de la semana, inventario completo y temperatura del frutero; responden
  al instante y sin LLM. Ollama en contenedor (perfil `ollama`) publicado en el puerto 11435.
- Problema / cómo lo resolví: el puerto 11434 chocaba con un Ollama instalado en el Mac → el
  contenedor se publica en 11435 y HA lo usa por la red interna (`http://ollama:11434`).
- Evidencia: [COMPLETAR: captura de Assist respondiendo "¿cuántas peras hay?"]

## Día 4 — dom 8 nov 2026
- Hice: primera medición del agente con `scripts/medir_agente.py`
  (`docs/resultados/agente_20261108_1700.md`).
- Problema / cómo lo resolví: el agente de Ollama (Qwen 2.5 3B) acertó 0/10 y tardó ~28 s por
  respuesta; respondía "no tengo información". Las oraciones locales acertaron 6/10 al instante; las
  4 que fallaron ("¿Me quedan manzanas? ¿Cuántas?", "temperatura del frutero") se corrigieron
  agregando oraciones. Limitar la CPU de Ollama en Docker Desktop no imita a la Pi (2,3 → 0,2
  tokens/s): los tiempos del documento se medirán en la Raspberry.
- Evidencia: informe de la medición.

## Días 5–7 — lun 9 a mié 11 nov 2026
- [COMPLETAR si trabajaste en el proyecto estos días]

## Día 8 — jue 12 nov 2026
- Hice: ESP32-S3 virtual con la webcam del Mac (`simulador/esp32_virtual.py`): cámara → modelo
  TFLite → lógica de confirmación anti-duplicados → teclas como botones → MQTT. Lógica de
  confirmación con 11 pruebas. Captura del dataset con la webcam. Firmware del sensor DHT en un
  ESP32. Panel FruitAI en HA. Guía de respaldo de la Pi sin copiar la SD completa. Muestra de
  Fruits-360 (150 fotos por fruta, solo las variedades que no se confunden).
- Problema / cómo lo resolví: sin el ESP32-S3 con cámara todavía → el Mac hace de ESP32 con los
  mismos mensajes MQTT. Respaldar la SD de 64 GB era inviable → todo el estado vive en la carpeta
  del proyecto (~8 MB sin los modelos de Ollama).
- Evidencia: [COMPLETAR: captura del ESP32 virtual confirmando una fruta y del panel]

## Día 9 — vie 13 nov 2026
- Hice: firmware principal del ESP32-S3 (`firmware/fruitai_camara/`): cámara OV2640, inferencia
  con la librería de Edge Impulse, botones con antirrebote, PIR que activa la cámara, LED de estado,
  DHT opcional y cola de movimientos si cae la red. La lógica anti-duplicados se tradujo a C++
  (`confirmacion.h`) con las mismas pruebas que la versión Python (24/24). Fotos propias con la
  webcam (manzana roja, manzana verde, banano, fondo).
- Problema / cómo lo resolví: al abrir la cámara se "desconectaba" el iPhone → era la Cámara de
  Continuidad, que macOS ponía como cámara 0; se agregó `--listar-camaras` y `FRUITAI_CAMARA`.
  El PIR no puede decidir que la fruta se retiró (no ve una fruta quieta) → solo activa la cámara;
  el retiro lo decide la cámara al ver "fondo".
- Evidencia: salida de `./scripts/probar_firmware.sh`.

## Día 10 — sáb 14 nov 2026
- Hice: entrenamiento en Edge Impulse y cinco versiones del modelo
  (`docs/resultados/cuantizacion_int8.md`); el v5 queda en `modelos/fruitai.tflite`. Agente de
  Ollama configurado en HA con el prompt nuevo; app de HA en el iPhone con acceso por Tailscale;
  notificaciones push; guía de puesta en marcha (`docs/puesta_en_marcha.md`).
- Problemas / cómo los resolví:
  1. MobileNetV2 0,35: float32 100 %, pero int8 solo 63–72 % (todo caía en "manzana roja").
     Reproduciendo el entrenamiento localmente y midiendo capa por capa se encontró la causa: la
     cuantización de las activaciones de la primera capa depthwise de MobileNetV2. Se cambió a
     MobileNetV1 0,25 → int8 84 %.
  2. Mi manzana verde fallaba (36–48 %) aunque la de Fruits-360 acertaba 100 %: 3 fotos verdes
     estaban etiquetadas como roja, 34 fotos estaban fuera del montaje y las 150 Granny Smith de
     Fruits-360 dominaban la clase. Se corrigieron etiquetas y se balanceó la clase.
  3. Con datos corregidos el float32 llegaba a 98 % pero el int8 seguía en 72 % → se reentrenó
     simulando int8 (quantization-aware training, `scripts/entrenar_qat.py`): int8 99,4 % en el set
     de prueba.
  4. En vivo la manzana verde salía como pera → 92 fotos nuevas en las posiciones reales de uso;
     v5: 100 % en las fotos nuevas no usadas al entrenar.
  5. En otros ambientes (pared, puerta, cara) el modelo falla: era esperado, funciona en el
     montaje para el que se entrenó (alcance del documento). Cuando duda no llega al 75 % y no
     registra nada.
  6. El iPhone no abría `http://` (exige HTTPS) → Tailscale con `tailscale serve` (solo mis
     dispositivos). Home Assistant devolvía 400 por el proxy → modo TLS-terminated TCP.
  7. Ollama quedaba publicado sin contraseña en la red → ahora solo en `127.0.0.1`.
  8. Medición del agente con el prompt nuevo y sin herramientas: Qwen 2.5 3B pasó de 0/10 y 28,6 s
     a 18/18 (10 comunes + 8 abiertas) y 0,7 s (`docs/resultados/agente_20261114_1438.md`).
  9. Registro desde Home Assistant: sensor "Fruta detectada" y botones Entrada / Salida que usan la
     fruta reconocida por el ESP32, con la misma lógica anti-duplicados; cámara en el panel (casi en
     vivo con `camera_view: live`). Sensor "ESP32 conectado".
  10. Documento nuevo `FruitAI_documento.docx` (el original corregido + arquitectura, desarrollo,
      pruebas y conclusiones, con diagramas).
- Evidencia: [COMPLETAR: capturas de la matriz de confusión de cada versión, del ESP32 virtual
  reconociendo la manzana verde y de la app en el iPhone]



## Día 11 — dom 15 nov 2026
- Hice: decisión de alcance. Como todo se va a manejar desde Home Assistant y no hay sensores
  ni recursos para la estación física, la versión actual queda en **Raspberry Pi + ESP32-S3 con
  cámara**, operada desde el panel (cámara, "Fruta detectada" y botones Entrada / Salida). La
  estación con caja y luz, los pulsadores, el PIR y el DHT22 pasan a mejoras futuras
  (`docs/mejoras_futuras.md`), con su plano y conexiones para no perder ese trabajo. En el
  firmware quedan programados pero desactivados (`USAR_BOTONES`, `USAR_PIR`, `USAR_DHT` en 0;
  `PUBLICAR_FOTO` en 1). Documento, guía, panel y diagramas actualizados al nuevo alcance.
- Problema / cómo lo resolví: sin DHT22 la tarjeta del frutero mostraba "desconocido" y la
  medición del agente fallaba en la pregunta de temperatura → se quitó la tarjeta del panel y
  `medir_agente.py` omite esa pregunta si no hay sensor.
- Evidencia: diagrama de despliegue (`docs/hardware/despliegue.png`).

---

## Plantilla para los próximos días

Copiar este bloque al final, una vez por día de trabajo.

```markdown
## Día N — <día> <fecha> 2026
- Hice:
- Problema / cómo lo resolví:
- Evidencia: (captura, informe en docs/resultados/, commit)
```

## Evidencias por reunir

Marcar con [x] cuando la captura esté guardada (por ejemplo en `docs/evidencias/`).

- [ ] Día 1: [COMPLETAR qué se hizo]
- [ ] Día 2: `simular_esp32.py escuchar` y la tabla `movimientos` (`./scripts/fruitai.sh db`)
- [ ] Día 3: Assist respondiendo "¿cuántas peras hay?"
- [ ] Día 8: ESP32 virtual confirmando una fruta y el panel FruitAI
- [ ] Día 9: salida de `./scripts/probar_firmware.sh` (24/24)
- [ ] Día 10: matrices de confusión de MobileNetV2 (v0) y del modelo final; ESP32 virtual con la
      manzana verde; la app en el iPhone con el panel; Assist respondiendo una pregunta abierta;
      notificación en el celular; registro con + / − desde el panel

## Próximos hitos (cada uno será un día de la bitácora)

- [ ] Prueba del modelo v5 como librería Arduino (Edge Impulse, modelo propio)
- [ ] Raspberry Pi: copiar el sistema desde el Mac y medir el agente (Qwen 2.5 3B frente a 1.5B)
- [ ] ESP32-S3: probar la cámara, cargar el firmware y fijarlo en su soporte
- [ ] Fotos con la cámara del ESP32, reentrenamiento y QAT
- [ ] Prueba final de 20 movimientos reales desde el panel de Home Assistant (objetivo específico 6)
