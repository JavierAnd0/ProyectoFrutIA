# Respaldo y restauración de FruitAI en la Raspberry Pi

No hace falta copiar la SD completa (64 GB). Todo el estado de FruitAI vive en la carpeta
del proyecto y pesa unos 8 MB sin los modelos de Ollama.

| Carpeta / archivo   | Qué guarda                                                  | ¿Respaldar? |
|---------------------|-------------------------------------------------------------|-------------|
| `homeassistant/`    | Configuración, usuario de HA, integraciones (`.storage/`)   | Sí          |
| `data/fruitai.db`   | Movimientos y lecturas de ambiente (SQLite)                 | Sí          |
| `mosquitto/`        | Usuarios MQTT (`config/passwd`) y mensajes retenidos        | Sí          |
| `.env`              | Claves                                                      | Sí          |
| `ollama/`           | Modelos (unos 4–5 GB)                                       | No: se vuelven a descargar |

> El respaldo contiene contraseñas (`.env`, `passwd`, `.storage/auth`). No lo compartas.

## Hacer un respaldo

### Con la Pi encendida y en la misma red (desde el Mac)

```bash
rsync -a --exclude=ollama javier@raspberrypi.local:~/ProyectoFrutIA/ ~/Desktop/fruitai-respaldo/
```

`rsync` solo copia lo que cambió. Para garantizar que las bases de datos no se copien a medio
escribir, detén antes los contenedores en la Pi (`docker compose stop`) y vuelve a
arrancarlos al terminar (`docker compose start`).

### Solo con la SD (Pi apagada, SD en el Mac)

macOS no lee la partición de Linux (ext4); se usa [anylinuxfs](https://github.com/nohajc/anylinuxfs).

```bash
brew install nohajc/anylinuxfs/anylinuxfs
diskutil list external          # buscar la SD: partición "Linux", p. ej. disk12s2
sudo anylinuxfs /dev/disk12s2   # dejar esta terminal abierta
```

En otra terminal:

```bash
sudo rsync -a --exclude=ollama /Volumes/rootfs/home/javier/ProyectoFrutIA/ ~/Desktop/fruitai-respaldo/ && sudo chown -R $(whoami) ~/Desktop/fruitai-respaldo
```

Al terminar, expulsa `rootfs` y `bootfs` desde el Finder antes de sacar la SD.

## Restaurar en una SD limpia

1. **Grabar la SD** con Raspberry Pi Imager: Raspberry Pi 5, **Raspberry Pi OS Lite (64-bit)**.
   En "Editar ajustes": el **mismo hostname** de antes, usuario **`javier`**, Wi-Fi y **SSH activado**.
   Con el mismo hostname, el ESP32 y el navegador encuentran la Pi sin cambios.

2. **Entrar a la Pi** (unos 2 minutos después de encenderla):
   ```bash
   ssh javier@raspberrypi.local
   ```

3. **Instalar Docker** (en la Pi). Después, `exit` y volver a entrar por `ssh`:
   ```bash
   curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker javier
   ```

4. **Copiar el respaldo** (desde el Mac):
   ```bash
   rsync -a ~/Desktop/fruitai-respaldo/ javier@raspberrypi.local:~/ProyectoFrutIA/
   ```

5. **Permisos de Mosquitto** (en la Pi). El broker solo acepta `passwd` si es suyo (uid 1883):
   ```bash
   cd ~/ProyectoFrutIA && sudo chown 1883:1883 mosquitto/config/passwd && sudo chmod 700 mosquitto/config/passwd && sudo chown -R 1883:1883 mosquitto/data
   ```

6. **Arrancar todo**:
   ```bash
   docker compose --profile ollama up -d --build
   ```

7. **Descargar el modelo** que usa el agente de HA:
   ```bash
   docker exec fruitai-ollama ollama pull qwen2.5:3b
   ```

8. **Comprobar**:
   ```bash
   ./scripts/fruitai.sh estado
   ```
   Abrir `http://raspberrypi.local:8123` y entrar con el mismo usuario de siempre.

**No hace falta:** el onboarding de HA, `scripts/crear_usuarios_mqtt.sh`, ni volver a
configurar MQTT u Ollama dentro de HA; todo viene en el respaldo.

**Si cambia el hostname o la IP de la Pi:** actualizar a dónde se conecta el ESP32
(`firmware/**/secrets.h`) y la URL con la que se abre HA.
