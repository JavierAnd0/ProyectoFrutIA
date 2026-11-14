import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, FancyArrowPatch, Polygon, Ellipse
plt.rcParams["font.family"] = "DejaVu Sans"
fig, ax = plt.subplots(figsize=(13, 6.6)); ax.set_xlim(0, 13); ax.set_ylim(0, 6.6); ax.axis("off")
ax.set_title("FruitAI funcionando en la casa", fontsize=13, weight="bold")

def zona(x, y, w, h, t):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15", fc="#fafaf7", ec="#bbb", lw=1.2))
    ax.text(x + .2, y + h - .25, t, fontsize=10.5, weight="bold", color="#555", va="top")

# Cocina
zona(0.2, 0.4, 4.6, 5.6, "Cocina")
ax.add_patch(Rectangle((0.4, 1.5), 4.2, .15, fc="#a9825a", ec="#6b4f2f"))   # mesón
ax.add_patch(Rectangle((1.0, 1.65), 2.0, 1.9, fc="#f4f3ee", ec="#888"))      # estación
ax.add_patch(Rectangle((1.0, 3.45), 2.0, .12, fc="#dcdad3", ec="#777"))
ax.add_patch(Rectangle((1.75, 3.3), .5, .15, fc="#1f5fa8", ec="#123"))
ax.add_patch(Polygon([(1.95, 3.3), (2.05, 3.3), (2.6, 1.8), (1.4, 1.8)], fc="#5aa0e0", alpha=.15, ec="none"))
ax.add_patch(Circle((2.0, 1.95), .25, fc="#7fbf3f", ec="#4a7a20"))
ax.add_patch(Rectangle((1.1, 1.2), 1.8, .3, fc="#4a4a4a", ec="#222"))
ax.text(2.0, 1.35, "+  ●  −", ha="center", va="center", color="w", fontsize=8)
ax.text(2.0, 3.8, "Estación\n(ESP32-S3)", ha="center", fontsize=9)
ax.add_patch(Ellipse((3.75, 1.85), 1.1, .35, fc="#c9a26b", ec="#8a6a3a"))
for i, c in enumerate(["#e8c22a", "#d23b2f", "#7fbf3f"]): ax.add_patch(Circle((3.4 + i * .35, 2.05), .17, fc=c, ec="#555"))
ax.add_patch(Rectangle((4.25, 1.65), .2, .35, fc="#f2f2f2", ec="#666")); ax.text(3.75, 1.25, "frutero + DHT22", ha="center", fontsize=8)
ax.add_patch(Rectangle((0.5, .55), .45, .35, fc="#eee", ec="#777")); ax.text(1.05, .72, "cargador USB 5 V", fontsize=7.5, va="center")

# Sala / router
zona(5.3, 0.4, 3.6, 5.6, "Sala (junto al router)")
ax.add_patch(Rectangle((5.6, 1.5), 3.0, .12, fc="#a9825a", ec="#6b4f2f"))
ax.add_patch(FancyBboxPatch((5.8, 1.62), 1.1, .45, boxstyle="round,pad=0.02", fc="#444", ec="#111"))
for i in range(3): ax.plot([6.0 + i * .35, 6.0 + i * .35 + .05], [2.07, 2.45], color="#222", lw=2)
ax.text(6.35, 2.75, "Router\nWi-Fi", ha="center", fontsize=9)
ax.add_patch(FancyBboxPatch((7.3, 1.62), 1.1, .5, boxstyle="round,pad=0.02", fc="#c51a4a", ec="#7a0f2c"))
ax.text(7.85, 1.87, "Pi 5", ha="center", va="center", color="w", fontsize=9, weight="bold")
ax.plot([6.9, 7.3], [1.8, 1.8], color="#1f77b4", lw=2)
ax.text(7.85, 2.75, "Raspberry Pi\n(cable de red)", ha="center", fontsize=9)
ax.text(7.1, 4.3, "Dentro de la Pi (Docker):\nMosquitto · servicio + SQLite\nHome Assistant · Ollama", ha="center", fontsize=8.5,
        bbox=dict(fc="#eef2f8", ec="#9fb3d1", boxstyle="round,pad=0.3"))

# Celular (en casa y fuera)
zona(9.4, 0.4, 3.4, 5.6, "Tu celular (en casa o fuera)")
ax.add_patch(FancyBboxPatch((10.35, 1.0), 1.5, 3.0, boxstyle="round,pad=0.02,rounding_size=0.2", fc="#222", ec="#000"))
ax.add_patch(Rectangle((10.45, 1.25), 1.3, 2.5, fc="#ffffff", ec="none"))
ax.text(11.1, 3.55, "FruitAI", ha="center", fontsize=8.5, weight="bold")
ax.add_patch(Rectangle((10.55, 2.6), 1.1, .8, fc="#ddd", ec="#aaa")); ax.text(11.1, 3.0, "cámara", ha="center", fontsize=7, color="#666")
ax.text(11.1, 2.35, "Fruta: kiwi ✓", ha="center", fontsize=7)
ax.add_patch(Circle((10.8, 1.95), .17, fc="#2e9e45")); ax.text(10.8, 1.95, "+", ha="center", va="center", color="w", fontsize=9, weight="bold")
ax.add_patch(Circle((11.4, 1.95), .17, fc="#c0392b")); ax.text(11.4, 1.95, "−", ha="center", va="center", color="w", fontsize=9, weight="bold")
ax.text(11.1, 1.45, "Banano 3 · Kiwi 1", ha="center", fontsize=6.5)
ax.text(11.1, 4.6, "«¿Qué fruta se\nestá acabando?»", ha="center", fontsize=8.5, style="italic",
        bbox=dict(fc="#f0e9f7", ec="#b9a3d6", boxstyle="round,pad=0.3"))
ax.text(11.1, 0.62, "notificación: «se acabaron los kiwis»", ha="center", fontsize=7.5, color="#5b3b80")

# conexiones inalámbricas
def onda(a, b, t, c="#2e6b35", dy=.18):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="<|-|>", mutation_scale=12, lw=1.4, color=c, ls=(0, (4, 3))))
    ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + dy, t, ha="center", fontsize=8.5, color=c, bbox=dict(fc="white", ec="none", pad=1))
onda((3.05, 2.9), (5.85, 2.25), "Wi-Fi · MQTT\n(movimientos, estado)")
onda((8.45, 2.0), (10.3, 2.5), "Wi-Fi en casa\no Tailscale (HTTPS)", c="#5b3b80")
fig.tight_layout(); fig.savefig("casa.png", dpi=170); print("ok")
