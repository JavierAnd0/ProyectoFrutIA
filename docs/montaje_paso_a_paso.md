# Montaje real: Raspberry Pi + ESP32-S3 con cámara

Checklist para pasar de la simulación en el Mac al sistema real. Cada fase se prueba antes
de seguir. Tiempo aproximado: 2–3 horas (la primera compilación del firmware tarda).

## Fase 0 — Qué respaldo usar

Hay dos estados guardados del sistema:

| Respaldo | Qué tiene | ¿Usarlo? |
|---|---|---|
| **La carpeta del proyecto en el Mac** (donde corriste todo en Docker) | Lo más nuevo: tu usuario y contraseña de HA, MQTT, el agente con el prompt nuevo, el panel, la app del celular, los movimientos de prueba | **Sí, este** |
| El respaldo antiguo de la Raspberry (`~/Desktop/fruitai-respaldo-sd`, del 12 de noviembre) | El estado de antes de la simulación en el Mac: sin el agente nuevo, sin el registro desde el panel. Su `.env` y su `passwd` de MQTT son otros, así que no se mezclan con los del Mac | Solo si perdiste lo del Mac (entonces copia esa carpeta completa, no partes) |

Del Mac se copian `homeassistant/`, `data/`, `mosquitto/` y `.env`. El código se baja de GitHub.

---

## Fase 1 — Raspberry Pi

### 1.1 Sistema operativo
- **Si la SD tiene el sistema de antes** y entras por SSH: sirve. Pasa a 1.3.
- **Si no:** en el Mac, Raspberry Pi Imager → *Raspberry Pi OS Lite (64-bit)* → en la
  configuración: nombre `raspberrypi`, usuario y clave, Wi-Fi (mejor cable de red) y **SSH
  activado**. Grabar, encender y entrar: `ssh <usuario>@raspberrypi.local`.

### 1.2 IP fija
En el router, reserva una IP para la Raspberry (ej. `192.168.1.20`). La necesitan el ESP32 y
la app.

### 1.3 Docker y el código (en la Raspberry)
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && exit
```
Vuelve a entrar por SSH y:
```bash
git clone -b claude/lucid-gauss-raw1x3 https://github.com/JavierAnd0/ProyectoFrutIA.git
```
(Si ya existía la carpeta: `cd ProyectoFrutIA && git pull origin claude/lucid-gauss-raw1x3`.)

**Si el repositorio es privado** (la Pi no tiene credenciales de GitHub), no clones: copia el
proyecto entero desde el Mac en el paso 1.4, que lleva código y estado juntos:
```bash
rsync -a --exclude=.venv --exclude=ollama --exclude=dataset ./ <usuario>@<IP-Pi>:~/ProyectoFrutIA/
```

**Red de la universidad o pública:** suelen aislar los equipos (el Mac no ve a la Pi) y la Pi
puede arrancar con la hora atrasada, lo que hace fallar `apt` con *Not live until…*. Arreglo:
`sudo date -s "AAAA-MM-DD HH:MM"` y `sudo timedatectl set-ntp true`; para entrar desde el Mac,
Tailscale (`sudo tailscale up --qr`) y `ssh` a su IP `100.x.y.z`.

### 1.4 Copiar el estado desde el Mac (en el Mac)
Primero detén el sistema del Mac (para que no haya dos brokers ni dos Home Assistant):
```bash
cd ~/ProyectoFrutIA && docker compose --profile ollama down && tailscale serve reset
```
Luego copia (cambia el usuario y la IP de la Pi):
```bash
rsync -av homeassistant data mosquitto .env <usuario>@192.168.1.20:~/ProyectoFrutIA/
```

### 1.5 Levantar todo (en la Raspberry)
Primero, permisos de Mosquitto: el broker solo acepta `passwd` si es suyo (uid 1883), y
`rsync` lo deja a nombre de tu usuario:
```bash
cd ~/ProyectoFrutIA && sudo chown 1883:1883 mosquitto/config/passwd && sudo chmod 700 mosquitto/config/passwd && sudo chown -R 1883:1883 mosquitto/data
```
Luego:
```bash
cd ~/ProyectoFrutIA && docker compose --profile ollama up -d --build
docker exec fruitai-ollama ollama pull qwen2.5:3b
./scripts/fruitai.sh estado
```
Deben verse 4 contenedores `Up`. Prueba sin ESP32: `./scripts/fruitai.sh entrada banano 2`.

### 1.6 Home Assistant
- Abre `http://192.168.1.20:8123` desde el Mac: entra con **tu mismo usuario y contraseña**.
- Ajustes → Sistema → Red → **Red local**: `http://192.168.1.20:8123`.
- Si el panel no muestra stock: Ajustes → Dispositivos y servicios → MQTT debe decir
  "conectado" (broker `mosquitto`). Si no, reinicia HA.

### 1.7 Celular por Tailscale (en la Raspberry)
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
sudo tailscale set --operator=$USER
sudo tailscale serve --bg --tls-terminated-tcp=443 tcp://localhost:8123
```
`tailscale serve status` muestra la nueva dirección (`https://raspberrypi.<tu-red>.ts.net`).
Ponla en HA (Ajustes → Sistema → Red → **Internet**) y en la app del celular (Ajustes de la
app → Servidor).

---

## Fase 2 — ESP32-S3 con cámara (en el Mac, con la placa por USB)

### 2.1 ¿Qué placa es?
En `firmware/fruitai_camara/fruitai_camara.ino`, deja activa la línea de tu placa:
`#define PLACA_FREENOVE_S3` (Freenove ESP32-S3 WROOM CAM / ESP32-S3-EYE) o
`#define PLACA_XIAO_S3` (Seeed XIAO ESP32S3 Sense). Si es otra, dime el modelo.

### 2.2 Arduino IDE
1. Gestor de placas → **esp32** de Espressif (3.x).
2. Gestor de librerías → **PubSubClient** (Nick O'Leary).
3. *Sketch → Include Library → Add .ZIP Library…* →
   `firmware/fruitai_camara/libreria/FruitAi_inferencing.zip` (el modelo, ya generado).

### 2.3 Probar solo la cámara
*Archivo → Ejemplos → ESP32 → Camera → CameraWebServer*: elige tu placa en `board_config.h`,
pon tu Wi-Fi, carga, abre la IP del monitor serie en el navegador y mira la imagen. Si aquí no
hay imagen, revisa el cable plano de la cámara antes de seguir.

### 2.4 Credenciales
```bash
cp firmware/fruitai_camara/secrets.h.example firmware/fruitai_camara/secrets.h
```
En `secrets.h`: Wi-Fi de **2,4 GHz**, `MQTT_HOST` = IP de la Raspberry, `MQTT_USUARIO` y
`MQTT_CLAVE` = `MQTT_USUARIO_ESP32` / `MQTT_CLAVE_ESP32` del `.env`.

### 2.5 Cargar el firmware
Herramientas: placa **ESP32S3 Dev Module** (Freenove) o **XIAO_ESP32S3**; **PSRAM: OPI
PSRAM**; **Partition Scheme: Huge APP (3MB No OTA)**; **USB CDC On Boot: Enabled** si el
monitor serie queda vacío. Cargar (la primera compilación tarda varios minutos).

Monitor serie a 115200, debe mostrar:
```
Modelo: 96x96, 6 clases: banano fondo kiwi manzana_roja manzana_verde pera
Wi-Fi OK (...). MQTT 192.168.1.20:1883 como esp32... OK
ve: fondo 98% (... ms) | ESPERANDO
```
Anota los **ms** de `ve:`: es el tiempo de inferencia real para el documento.

### 2.6 En el panel de Home Assistant
"ESP32 conectado" activo, la cámara visible, y con una fruta debajo "Fruta detectada" la
muestra como CONFIRMADA. Pulsa **Entrada**: el stock sube.

---

## Fase 3 — Ubicar la cámara y mejorar la precisión

1. Fija el ESP32 mirando hacia abajo a 25–30 cm de un fondo claro, con luz pareja.
2. El modelo actual se entrenó con fotos de la webcam. Para la cámara real, toma fotos con
   ella (en el Mac, con el ESP32 encendido):
   ```bash
   .venv/bin/python scripts/capturar_desde_esp32.py banano --fotos 50 --host 192.168.1.20
   ```
   Repite por fruta (gírala y muévela mientras guarda) y `fondo --fotos 100`.
3. Súbelas a Edge Impulse (o pásamelas en un zip) y reentreno con QAT; luego regeneramos
   la librería y vuelves a cargar el firmware.

## Fase 4 — Prueba final (objetivo 6)

20 movimientos desde el panel, mezclando frutas, entradas y salidas, incluyendo: pulsar
Entrada dos veces, cambiar de fruta sin retirarla y salida con stock 0. Anota por cada uno:
fruta, tipo, si se registró bien y segundos hasta CONFIRMADA. Compara con
`./scripts/fruitai.sh db`.

| # | Fruta | Tipo | ¿Bien? | Seg. hasta confirmar | Nota |
|---|---|---|---|---|---|
| 1 | | | | | |
