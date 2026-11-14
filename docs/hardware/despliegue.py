# Diagrama de despliegue (notación UML de nodos y componentes), en blanco y negro.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5})
K, G = "#111111", "#666666"
fig = plt.figure(figsize=(11.7, 6.2))
ax = fig.add_axes([0.01, 0.01, 0.98, 0.98]); ax.set_xlim(0, 297); ax.set_ylim(0, 157); ax.axis("off"); ax.set_aspect("equal")

def nodo(x, y, w, h, estereotipo, nombre, d=5):
    ax.add_patch(Polygon([(x, y + h), (x + d, y + h + d), (x + w + d, y + h + d), (x + w, y + h)], fc="white", ec=K, lw=.9))
    ax.add_patch(Polygon([(x + w, y), (x + w + d, y + d), (x + w + d, y + h + d), (x + w, y + h)], fc="white", ec=K, lw=.9))
    ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=K, lw=1.1))
    ax.text(x + w / 2, y + h - 4, f"«{estereotipo}»", ha="center", fontsize=7, color=G)
    ax.text(x + w / 2, y + h - 9, nombre, ha="center", fontsize=9, weight="bold")

def componente(x, y, w, h, estereotipo, nombre, lineas=()):
    ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=K, lw=.8))
    ix, iy = x + w - 7, y + h - 6                       # icono de componente UML
    ax.add_patch(Rectangle((ix, iy), 5, 4, fc="white", ec=K, lw=.6))
    ax.add_patch(Rectangle((ix - 1.2, iy + 2.4), 2.4, 1, fc="white", ec=K, lw=.5))
    ax.add_patch(Rectangle((ix - 1.2, iy + .6), 2.4, 1, fc="white", ec=K, lw=.5))
    ax.text(x + 3, y + h - 3.5, f"«{estereotipo}»", fontsize=6.3, color=G, va="top")
    ax.text(x + 3, y + h - 8, nombre, fontsize=7.8, weight="bold", va="top")
    for i, l in enumerate(lineas):
        ax.text(x + 3, y + h - 13.5 - i * 4.2, l, fontsize=6.6, va="top")

def enlace(p, q, texto=None, pos=0.5, off=(0, 2.5), ha="center", estilo="-"):
    ax.plot([p[0], q[0]], [p[1], q[1]], color=K, lw=.8, ls=estilo)
    if texto:
        ax.text(p[0] + (q[0] - p[0]) * pos + off[0], p[1] + (q[1] - p[1]) * pos + off[1], texto, ha=ha, fontsize=6.6,
                bbox=dict(fc="white", ec="none", pad=.6))

# ---------------- ESP32-S3 ----------------
nodo(8, 40, 66, 82, "dispositivo", "ESP32-S3")
componente(13, 72, 56, 34, "firmware", "fruitai_camara",
           ["modelo TinyML int8 (300 KB)", "lógica de confirmación", "cola de movimientos", "cliente MQTT"])
ax.text(13, 61, "Periféricos:", fontsize=6.8, weight="bold")
for i, l in enumerate(["cámara OV2640", "pulsadores ENTRADA / SALIDA", "PIR AM312 · LED", "DHT22"]):
    ax.text(15, 56.5 - i * 4.2, "· " + l, fontsize=6.6)

# ---------------- Raspberry Pi 5 ----------------
nodo(102, 12, 112, 128, "dispositivo", "Raspberry Pi 5")
ax.text(158, 125, "«entorno de ejecución» Docker", ha="center", fontsize=6.8, color=G)
ax.add_patch(Rectangle((106, 16), 104, 105, fill=False, ec=G, lw=.6, ls=(0, (4, 2))))
componente(110, 92, 44, 24, "contenedor", "Mosquitto", ["broker MQTT", "usuario por cliente"])
componente(162, 92, 44, 24, "contenedor", "Home Assistant", ["panel · avisos · Assist", "registro + / −"])
componente(110, 56, 44, 26, "contenedor", "servicio", ["valida y guarda", "calcula stock y resúmenes"])
componente(162, 56, 44, 26, "contenedor", "Ollama", ["Qwen 2.5 3B", "solo 127.0.0.1"])
componente(110, 21, 44, 25, "artefacto", "fruitai.db", ["SQLite: movimientos,", "ambiente"])

# enlaces internos
enlace((132, 92), (132, 82), "MQTT", pos=.5, off=(6, -1.5))
enlace((154, 104), (162, 104), "MQTT", pos=.5, off=(0, 2.2))
enlace((184, 92), (184, 82), "HTTP\n11434", pos=.5, off=(8, -3))
enlace((132, 56), (132, 46), "lee / escribe", pos=.5, off=(11, -1.5))

# ---------------- Celular ----------------
nodo(242, 58, 46, 52, "dispositivo", "Celular")
componente(246, 66, 38, 26, "app", "Home Assistant", ["panel, chat,", "notificaciones"])

# enlaces entre nodos
enlace((69, 95), (110, 106), "MQTT · TCP 1883\nWi-Fi (LAN)", pos=.5, off=(0, 4))
enlace((206, 104), (246, 82), "HTTPS 443 · Tailscale\n(o HTTP 8123 en la LAN)", pos=.55, off=(6, 8))

ax.text(148.5, 4, "Diagrama de despliegue de FruitAI: qué corre en cada equipo y por qué protocolo se comunican.",
        ha="center", fontsize=7, style="italic", color=G)
fig.savefig("despliegue.png", dpi=220); print("ok")
