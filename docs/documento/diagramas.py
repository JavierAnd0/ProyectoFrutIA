import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
plt.rcParams["font.family"] = "DejaVu Serif"

def caja(ax, x, y, w, h, titulo, lineas=(), color="#e8eef7", borde="#2f4a73"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=color, ec=borde, lw=1.4))
    ax.text(x + w / 2, y + h - 0.22, titulo, ha="center", va="top", fontsize=10.5, weight="bold", color="#1b2a44")
    for i, l in enumerate(lineas):
        ax.text(x + w / 2, y + h - 0.6 - i * 0.3, l, ha="center", va="top", fontsize=8.5, color="#222")

def flecha(ax, a, b, texto="", dy=0.12, doble=False):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="<|-|>" if doble else "-|>", mutation_scale=12, lw=1.3, color="#444"))
    if texto:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + dy, texto, ha="center", va="bottom", fontsize=8, color="#333",
                bbox=dict(fc="white", ec="none", pad=1))

# ---------- Arquitectura ----------
fig, ax = plt.subplots(figsize=(10, 4.6)); ax.set_xlim(0, 10); ax.set_ylim(0, 4.6); ax.axis("off")
caja(ax, 0.1, 1.3, 2.5, 2.35, "ESP32-S3 con cámara",
     ["Cámara OV2640", "Modelo TinyML (int8)", "Lógica de confirmación", "Cliente MQTT",
      "Foto al panel"], color="#eaf5ea", borde="#2e6b35")
ax.add_patch(FancyBboxPatch((3.55, 0.15), 3.3, 4.2, boxstyle="round,pad=0.02,rounding_size=0.08", fc="#f6f6f6", ec="#777", lw=1, ls="--"))
ax.text(5.2, 4.3, "Raspberry Pi (Docker)", ha="center", va="top", fontsize=10.5, weight="bold", color="#333")
caja(ax, 3.8, 3.0, 2.8, 0.85, "Mosquitto", ["broker MQTT con usuarios"])
caja(ax, 3.8, 1.75, 2.8, 0.85, "Servicio (Python)", ["valida, guarda, calcula stock"])
caja(ax, 3.8, 0.35, 1.3, 0.95, "SQLite", ["historial"])
caja(ax, 5.3, 0.35, 1.3, 0.95, "Ollama", ["Qwen 2.5"])
caja(ax, 7.6, 1.75, 2.3, 2.1, "Home Assistant", ["panel · avisos", "Assist (chat)", "registro + / −"], color="#fdf1e3", borde="#8a5a1c")
caja(ax, 7.75, 0.2, 2.0, 0.95, "App del celular", ["Tailscale (HTTPS)"], color="#f0e9f7", borde="#5b3b80")
flecha(ax, (2.6, 3.0), (3.8, 3.4), doble=True)
ax.text(3.15, 3.45, "MQTT (Wi-Fi)", ha="center", fontsize=8, style="italic", color="#2e6b35")
flecha(ax, (5.2, 3.0), (5.2, 2.6), doble=True)
flecha(ax, (4.45, 1.75), (4.45, 1.3), doble=True)
flecha(ax, (6.6, 3.4), (7.6, 3.2), doble=True)
ax.text(7.1, 3.5, "discovery", ha="center", fontsize=8, color="#333")
flecha(ax, (7.6, 2.0), (6.6, 0.9), doble=True)
ax.text(7.25, 1.2, "preguntas\nabiertas", ha="center", fontsize=8, color="#333")
flecha(ax, (8.75, 1.75), (8.75, 1.15), doble=True)
fig.tight_layout(); fig.savefig("arquitectura.png", dpi=200); plt.close(fig)

# ---------- Máquina de estados ----------
fig, ax = plt.subplots(figsize=(10, 3.4)); ax.set_xlim(0, 10); ax.set_ylim(0, 3.4); ax.axis("off")
for x, n, l, c in [(0.3, "ESPERANDO", "LED apagado", "#eeeeee"), (3.8, "CONFIRMADA", "LED fijo", "#eaf5ea"),
                   (7.3, "REGISTRADA", "LED parpadea", "#fdf1e3")]:
    caja(ax, x, 1.3, 2.4, 0.95, n, [l], color=c)
flecha(ax, (2.7, 1.78), (3.8, 1.78))
ax.text(3.25, 2.4, "5 fotogramas seguidos\nmisma fruta, conf. ≥ 0,75", ha="center", fontsize=8, color="#333")
flecha(ax, (6.2, 1.78), (7.3, 1.78))
ax.text(6.75, 2.4, "Entrada / Salida en el panel\n→ 1 movimiento", ha="center", fontsize=8, color="#333")
ax.add_patch(FancyArrowPatch((8.5, 1.3), (1.5, 1.3), connectionstyle="arc3,rad=-0.3", arrowstyle="-|>",
                             mutation_scale=12, lw=1.3, color="#444"))
ax.text(5, 0.62, "fruta retirada: «fondo» durante 5 fotogramas", ha="center", fontsize=8.5, color="#333")
ax.text(1.5, 2.55, "Entrada/Salida: ignorado", ha="center", fontsize=8.5, color="#8a1c1c")
ax.text(8.5, 2.55, "más pulsaciones: ignoradas", ha="center", fontsize=8.5, color="#8a1c1c")
fig.tight_layout(); fig.savefig("estados.png", dpi=200); plt.close(fig)
print("ok")
