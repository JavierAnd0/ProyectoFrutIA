import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, Ellipse, FancyBboxPatch, FancyArrowPatch
plt.rcParams["font.family"] = "DejaVu Sans"

fig, axs = plt.subplots(1, 2, figsize=(13, 6.2), gridspec_kw={"width_ratios": [1.15, 1]})

# ---------------- Vista en perspectiva ----------------
ax = axs[0]; ax.set_xlim(0, 11); ax.set_ylim(0, 10); ax.axis("off"); ax.set_aspect("equal")
ax.set_title("Estación de registro (vista en perspectiva)", fontsize=12, weight="bold")
d = (1.6, 1.1)  # desplazamiento de profundidad
x0, y0, W, H = 1.5, 1.2, 6.0, 6.0
# caja: fondo, lados, techo (abierta por delante)
fondo = [(x0 + d[0], y0 + d[1]), (x0 + W + d[0], y0 + d[1]), (x0 + W + d[0], y0 + H + d[1]), (x0 + d[0], y0 + H + d[1])]
ax.add_patch(Polygon(fondo, fc="#fbfbf8", ec="#999", lw=1))
ax.add_patch(Polygon([(x0, y0), (x0 + d[0], y0 + d[1]), (x0 + d[0], y0 + H + d[1]), (x0, y0 + H)], fc="#f0efe9", ec="#888"))
ax.add_patch(Polygon([(x0 + W, y0), (x0 + W + d[0], y0 + d[1]), (x0 + W + d[0], y0 + H + d[1]), (x0 + W, y0 + H)], fc="#e9e8e2", ec="#888"))
ax.add_patch(Polygon([(x0, y0), (x0 + W, y0), (x0 + W + d[0], y0 + d[1]), (x0 + d[0], y0 + d[1])], fc="#ffffff", ec="#888"))  # base blanca
ax.add_patch(Polygon([(x0, y0 + H), (x0 + W, y0 + H), (x0 + W + d[0], y0 + H + d[1]), (x0 + d[0], y0 + H + d[1])], fc="#dcdad3", ec="#777"))  # techo
# tira LED en el techo
ax.add_patch(Polygon([(x0 + 0.6, y0 + H - 0.05), (x0 + W - 0.6, y0 + H - 0.05), (x0 + W - 0.6 + d[0] * .5, y0 + H - .05 + d[1] * .5),
                      (x0 + .6 + d[0] * .5, y0 + H - .05 + d[1] * .5)], fc="#fff6b0", ec="#d4b400", lw=1))
# haz de luz
ax.add_patch(Polygon([(x0 + 1.2, y0 + H - .1), (x0 + W - 1.2, y0 + H - .1), (x0 + W - .3, y0 + .4), (x0 + .5, y0 + .4)], fc="#fff6b0", alpha=.25, ec="none"))
# ESP32 + cámara en el techo, mirando hacia abajo
cx, cy = x0 + W / 2 + .8, y0 + H + .25
ax.add_patch(FancyBboxPatch((cx - .9, cy - .25), 1.8, .5, boxstyle="round,pad=0.02", fc="#1f5fa8", ec="#123"))
ax.add_patch(Circle((cx, cy - .3), .18, fc="#222", ec="#000"))
ax.add_patch(Polygon([(cx - .15, cy - .45), (cx + .15, cy - .45), (cx + 1.3, y0 + .7), (cx - 1.3, y0 + .7)], fc="#5aa0e0", alpha=.12, ec="#5aa0e0", ls="--"))
# fruta (manzana) sobre la base
ax.add_patch(Ellipse((cx, y0 + .75), 1.15, .55, fc="#000", alpha=.08))
ax.add_patch(Circle((cx, y0 + 1.05), .5, fc="#d23b2f", ec="#8e1f17"))
ax.plot([cx, cx + .08], [y0 + 1.5, y0 + 1.75], color="#5a3a1a", lw=2)
# panel frontal (sobre la base, al frente)
px, py = x0 + .3, y0 - 1.0
ax.add_patch(Rectangle((px, py), W - .6, .85, fc="#4a4a4a", ec="#222"))
ax.add_patch(Circle((px + 1.0, py + .43), .28, fc="#2e9e45", ec="#145a24"))
ax.text(px + 1.0, py + .43, "+", ha="center", va="center", color="w", fontsize=14, weight="bold")
ax.add_patch(Circle((px + W - 1.6, py + .43), .28, fc="#c0392b", ec="#7a1f15"))
ax.text(px + W - 1.6, py + .43, "−", ha="center", va="center", color="w", fontsize=14, weight="bold")
ax.add_patch(Circle((px + (W - .6) / 2, py + .43), .13, fc="#5fd16f", ec="#2a7a34"))
# PIR en el borde delantero
ax.add_patch(Circle((x0 + W - .4, y0 + .35), .22, fc="#f2f2f2", ec="#777"))
# DHT22 afuera, junto al frutero
ax.add_patch(Rectangle((9.5, 1.3), .45, .7, fc="#f4f4f4", ec="#666"))
ax.plot([9.72, 9.0, 8.4], [1.3, 0.9, 0.9], color="#888", lw=1, ls=":")
ax.add_patch(Ellipse((9.0, 2.75), 1.6, .5, fc="#c9a26b", ec="#8a6a3a"))
for i, col in enumerate(["#e8c22a", "#7fbf3f", "#d23b2f"]):
    ax.add_patch(Circle((8.55 + i * .42, 3.05), .22, fc=col, ec="#555"))
# rótulos
def rot(xy, xyt, t):
    ax.annotate(t, xy=xy, xytext=xyt, fontsize=8.6, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color="#555", lw=.8))
rot((cx + .9, cy), (8.3, 9.3), "ESP32-S3 + cámara OV2640\n(en el techo, mirando hacia abajo)")
rot((x0 + 2.0, y0 + H + .2), (0.0, 9.4), "Tira LED blanca\n(luz fija)")
rot((x0 + 1.0, y0 + .4), (0.0, 0.6), "Base y paredes\nblanco mate")
rot((cx - .4, y0 + 1.1), (3.2, 4.2), "Fruta (una a la vez)")
rot((px + 1.0, py + .15), (0.3, -0.3), "Botón ENTRADA (+)")
rot((px + W - 1.6, py + .15), (5.3, -0.3), "Botón SALIDA (−)")
rot((px + (W - .6) / 2, py + .7), (2.4, -0.9), "LED de estado")
rot((x0 + W - .4, y0 + .55), (7.9, 6.0), "PIR (presencia)\nborde delantero")
rot((9.72, 2.0), (9.2, 4.6), "DHT22 junto\nal frutero")
ax.set_ylim(-1.3, 10)

# ---------------- Corte lateral con medidas ----------------
ax = axs[1]; ax.set_xlim(0, 10); ax.set_ylim(-0.5, 10); ax.axis("off"); ax.set_aspect("equal")
ax.set_title("Corte lateral y medidas", fontsize=12, weight="bold")
bx, by, bw, bh = 2.0, 1.0, 6.0, 6.0   # 30 x 30 cm → 1 unidad = 5 cm
ax.add_patch(Rectangle((bx, by), bw, .15, fc="#ddd", ec="#555"))          # base
ax.add_patch(Rectangle((bx + bw - .15, by), .15, bh, fc="#ddd", ec="#555"))  # pared trasera
ax.add_patch(Rectangle((bx, by + bh), bw, .15, fc="#ddd", ec="#555"))      # techo
ax.text(bx - .1, by + bh / 2, "frente\n(abierto)", ha="right", va="center", fontsize=8.5, color="#555")
ax.add_patch(FancyBboxPatch((bx + 2.4, by + bh - .35), 1.2, .3, boxstyle="round,pad=0.02", fc="#1f5fa8", ec="#123"))
ax.add_patch(Polygon([(bx + 2.95, by + bh - .38), (bx + 3.05, by + bh - .38), (bx + 4.6, by + .4), (bx + 1.4, by + .4)],
                     fc="#5aa0e0", alpha=.15, ec="#5aa0e0", ls="--"))
ax.add_patch(Rectangle((bx + .6, by + bh - .12), 1.4, .1, fc="#fff6b0", ec="#d4b400"))
ax.add_patch(Rectangle((bx + 4.0, by + bh - .12), 1.4, .1, fc="#fff6b0", ec="#d4b400"))
ax.add_patch(Circle((bx + 3.0, by + .65), .5, fc="#d23b2f", ec="#8e1f17"))
ax.add_patch(Rectangle((bx - .9, by - .55), 1.6, .5, fc="#4a4a4a", ec="#222"))
ax.text(bx - .1, by - .3, "+  ●  −", ha="center", va="center", color="w", fontsize=9)
ax.add_patch(Circle((bx + .35, by + .3), .15, fc="#f2f2f2", ec="#777"))
def cota(x1, y1, x2, y2, t, off=(0, 0)):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="<|-|>", mutation_scale=9, lw=.9, color="#b03030"))
    ax.text((x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], t, ha="center", va="center", fontsize=9, color="#b03030",
            bbox=dict(fc="white", ec="none", pad=1))
cota(bx, by + bh + .7, bx + bw, by + bh + .7, "≈ 30 cm")
cota(bx + bw + .6, by, bx + bw + .6, by + bh, "≈ 30 cm", off=(.0, 0))
cota(bx + 4.9, by + .15, bx + 4.9, by + bh - .35, "25–30 cm\ncámara → base", off=(.0, 0))
ax.text(5.0, 8.85, "La fruta debe llenar buena parte del cuadro de la cámara", ha="center", fontsize=8.5, style="italic", color="#444")
ax.text(5.0, -0.3, "La cámara y la luz siempre en el mismo lugar", ha="center", fontsize=8.5, color="#444")
fig.tight_layout(); fig.savefig("estacion.png", dpi=170); print("ok")
