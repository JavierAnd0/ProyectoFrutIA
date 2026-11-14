# Plano técnico de la estación de registro (unidades: cm)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "hatch.linewidth": 0.5})
K, LW, G = "#111111", 0.9, "#777777"
fig = plt.figure(figsize=(11.7, 8.3))   # A4 horizontal
ax = fig.add_axes([0.02, 0.02, 0.96, 0.96]); ax.set_xlim(0, 297); ax.set_ylim(0, 210); ax.axis("off"); ax.set_aspect("equal")
ax.add_patch(Rectangle((5, 5), 287, 200, fill=False, ec=K, lw=1.4))                     # marco
E = 2.0  # escala de dibujo: 1 cm real = 2 mm de lámina (1:5)

def rect(x, y, w, h, **k): ax.add_patch(Rectangle((x, y), w, h, fill=k.pop("fill", False), ec=k.pop("ec", K), lw=k.pop("lw", LW), **k))
def corte(x, y, w, h): rect(x, y, w, h, fill=True, fc="white", hatch="////", lw=LW)
def cota(x1, y1, x2, y2, t, d=6, lado=1):
    # línea de cota paralela al segmento (horizontal o vertical)
    if y1 == y2:
        yy = y1 + d * lado
        ax.plot([x1, x1], [y1, yy + 1.5 * lado], color=G, lw=.5); ax.plot([x2, x2], [y2, yy + 1.5 * lado], color=G, lw=.5)
        ax.annotate("", xy=(x1, yy), xytext=(x2, yy), arrowprops=dict(arrowstyle="<|-|>", lw=.6, color=K, mutation_scale=6))
        ax.text((x1 + x2) / 2, yy + 1.2 * lado, t, ha="center", va="bottom" if lado > 0 else "top", fontsize=7)
    else:
        xx = x1 + d * lado
        ax.plot([x1, xx + 1.5 * lado], [y1, y1], color=G, lw=.5); ax.plot([x2, xx + 1.5 * lado], [y2, y2], color=G, lw=.5)
        ax.annotate("", xy=(xx, y1), xytext=(xx, y2), arrowprops=dict(arrowstyle="<|-|>", lw=.6, color=K, mutation_scale=6))
        ax.text(xx + 1.2 * lado, (y1 + y2) / 2, t, ha="left" if lado > 0 else "right", va="center", rotation=90, fontsize=7)
def globo(n, x, y, xt, yt):
    ax.plot([x, xt], [y, yt], color=K, lw=.5); ax.add_patch(Circle((x, y), .6, color=K))
    ax.add_patch(Circle((xt, yt), 3.2, fc="white", ec=K, lw=.7)); ax.text(xt, yt, str(n), ha="center", va="center", fontsize=7.5, weight="bold")
def titulo(x, y, t): ax.text(x, y, t, ha="center", fontsize=8.5, weight="bold"); ax.plot([x - 18, x + 18], [y - 1.5, y - 1.5], color=K, lw=.6)

T, W, H, D, LIP = 0.5 * E, 30 * E, 30 * E, 30 * E, 5 * E   # espesor 5 mm, caja 30x30x30, frente 5 cm

# ---------------- VISTA FRONTAL ----------------
fx, fy = 30, 118
titulo(fx + W / 2, fy + H + 18, "VISTA FRONTAL")
rect(fx, fy, T, H); rect(fx + W - T, fy, T, H); rect(fx, fy + H - T, W, T); rect(fx, fy, W, T)  # laterales, techo, base
rect(fx + T, fy + T, W - 2 * T, H - 2 * T, lw=.4, ec=G)                                          # pared del fondo
cam_w = 4.0 * E; rect(fx + W / 2 - cam_w / 2, fy + H - T - 1.2 * E, cam_w, 1.2 * E)              # ESP32 en el techo
ax.add_patch(Circle((fx + W / 2, fy + H - T - 1.6 * E), .8 * E, fill=False, ec=K, lw=LW))        # lente
rect(fx + 3 * E, fy + H - T - .4 * E, 8 * E, .4 * E); rect(fx + W - 11 * E, fy + H - T - .4 * E, 8 * E, .4 * E)  # tiras LED
ax.add_patch(Circle((fx + W / 2, fy + T + 4 * E), 4 * E, fill=False, ec=G, lw=.6, ls="--"))     # fruta (referencia)
rect(fx, fy - LIP, W, LIP)                                                                       # frente con botones
for xb, s in ((7, "+"), (23, "−")):
    ax.add_patch(Circle((fx + xb * E, fy - LIP / 2), 1.2 * E, fill=False, ec=K, lw=LW)); ax.text(fx + xb * E, fy - LIP / 2, s, ha="center", va="center", fontsize=8)
ax.add_patch(Circle((fx + 15 * E, fy - LIP / 2), .4 * E, fill=False, ec=K, lw=LW))               # LED
ax.add_patch(Polygon([(fx + 13.8 * E, fy), (fx + 16.2 * E, fy), (fx + 15.6 * E, fy + .9 * E), (fx + 14.4 * E, fy + .9 * E)], fill=False, ec=K, lw=LW))  # PIR
cota(fx, fy + H, fx + W, fy + H, "300", d=7)
cota(fx + W, fy, fx + W, fy + H, "300", d=7)
cota(fx + W, fy - LIP, fx + W, fy, "50", d=7)
cota(fx + 7 * E, fy - LIP, fx + 23 * E, fy - LIP, "160", d=-6, lado=1)
globo(2, fx + W / 2 + cam_w / 2, fy + H - T - .6 * E, fx + W / 2 + 18, fy + H + 13)
globo(3, fx + 7 * E, fy + H - T - .2 * E, fx - 9, fy + H + 6)
globo(4, fx + 7 * E - 1.2 * E, fy - LIP / 2, fx - 10, fy - LIP / 2)
globo(5, fx + 23 * E + 1.2 * E, fy - LIP / 2, fx + W - 6, fy - LIP - 16)
globo(6, fx + 15 * E, fy - LIP / 2 - .4 * E, fx + 15 * E, fy - LIP - 16)
globo(7, fx + 15 * E, fy + .9 * E, fx + 8 * E, fy + 14)

# ---------------- CORTE A-A (lateral) ----------------
sx, sy = 125, 118
titulo(sx + D / 2, sy + H + 18, "CORTE A-A (LATERAL)")
corte(sx, sy, D, T); corte(sx + D - T, sy, T, H); corte(sx, sy + H - T, D, T)          # base, pared trasera, techo
corte(sx, sy - LIP, T, LIP + T)                                                         # frente del zócalo
corte(sx + D - T, sy - LIP, T, LIP)                                                     # trasera del zócalo
corte(sx, sy - LIP, D, T)                                                               # fondo del zócalo
ax.text(sx + D / 2, sy - LIP / 2, "zócalo: botones, LED y cables", ha="center", va="center", fontsize=6.3, color=G)
cy0 = sy + H - T
rect(sx + 13 * E, cy0 - 1.2 * E, 4 * E, 1.2 * E); rect(sx + 14.4 * E, cy0 - 2.0 * E, 1.2 * E, .8 * E)   # placa y lente
camx = sx + 15 * E
for dx in (-11, 11): ax.plot([camx, camx + dx * E], [cy0 - 2 * E, sy + T], color=G, lw=.6, ls=(0, (6, 3)))
ax.text(camx + 7.5 * E, sy + 13 * E, "campo de\nvisión", fontsize=6.5, color=G, ha="center")
ax.add_patch(Circle((camx, sy + T + 4 * E), 4 * E, fill=False, ec=G, lw=.6, ls="--"))
rect(sx + 4 * E, cy0 - .4 * E, 7 * E, .4 * E); rect(sx + 19 * E, cy0 - .4 * E, 7 * E, .4 * E)
ax.plot([sx + D - T, sx + D + 6], [sy - LIP / 2, sy - LIP / 2], color=K, lw=.6, ls=(0, (2, 1.5)))           # cable USB
cota(sx, sy + H, sx + D, sy + H, "300", d=7)
cota(camx, sy + T, camx, cy0 - 2 * E, "250 – 280", d=-24, lado=1)
ax.text(sx - 4, sy + H / 2, "FRENTE\n(abierto)", ha="right", va="center", fontsize=6.5, color=G)
globo(8, camx, sy + T + 1, sx + D + 14, sy + 16)
globo(9, sx + D + 4, sy - LIP / 2, sx + D + 14, sy - LIP - 9)
globo(1, sx + D - T / 2, sy + H / 2, sx + D + 14, sy + H / 2)

# ---------------- VISTA SUPERIOR ----------------
tx, ty = 212, 118
titulo(tx + W / 2, ty + D + 18, "VISTA SUPERIOR (SIN TECHO)")
rect(tx, ty, W, D); rect(tx + T, ty + T, W - 2 * T, D - 2 * T, lw=.4, ec=G)
ax.plot([tx, tx + W], [ty, ty], color="white", lw=2.2); ax.plot([tx, tx + W], [ty, ty], color=K, lw=.6, ls=(0, (6, 3)))  # frente abierto
ax.text(tx + W / 2 - 4, ty - 4, "frente abierto", ha="right", va="top", fontsize=6.5, color=G)
z = 15 * E; rect(tx + W / 2 - z / 2, ty + D / 2 - z / 2, z, z, ls=(0, (4, 2)), lw=.7)                   # zona de la fruta
rect(tx + W / 2 - 2 * E, ty + D / 2 - 1.4 * E, 4 * E, 2.8 * E, ls=(0, (1.5, 1.5)), lw=.6)             # cámara (oculta)
cota(tx, ty + D, tx + W, ty + D, "300", d=9)
cota(tx + W, ty, tx + W, ty + D, "300", d=6)
cota(tx + W / 2 - z / 2, ty + D / 2 - z / 2, tx + W / 2 + z / 2, ty + D / 2 - z / 2, "150", d=-6)
ax.text(tx + W / 2, ty + D / 2 + z / 2 + 2, "zona de la fruta", ha="center", fontsize=6.5)
ax.plot([tx + W / 2 - 3, tx + W / 2 + 3], [ty + D, ty + D], color=K, lw=0)
# línea de corte A-A
ax.plot([tx + W / 2, tx + W / 2], [ty - 8, ty + D + 7], color=K, lw=.6, ls=(0, (10, 2, 2, 2)))
for yy, va in ((ty - 9, "top"), (ty + D + 2, "bottom")): ax.text(tx + W / 2 + 2, yy, "A", fontsize=8, weight="bold", va=va)

# ---------------- LISTA DE PIEZAS ----------------
lx, ly = 12, 76
filas = [("Nº", "Pieza", "Cant.", "Notas"),
         ("1", "Caja con zócalo (MDF 5 mm o cartón)", "1", "interior blanco mate; zócalo de 50 mm"),
         ("2", "ESP32-S3 con cámara OV2640", "1", "en el techo, centrada, lente hacia abajo"),
         ("3", "Tira LED blanca USB", "2", "a los lados de la cámara; luz fija"),
         ("4", "Pulsador ENTRADA (+)", "1", "GPIO14 y GND"),
         ("5", "Pulsador SALIDA (−)", "1", "GPIO21 y GND"),
         ("6", "LED de estado", "1", "el de la placa o uno de 5 mm (220 Ω)"),
         ("7", "Sensor PIR AM312", "1", "borde superior del frente; GPIO1"),
         ("8", "Zona de la fruta", "—", "150 × 150 mm marcados en la base"),
         ("9", "Cable USB-C a cargador 5 V / 2 A", "1", "sale por la pared trasera"),
         ("—", "DHT22 (fuera de la caja)", "1", "junto al frutero; GPIO47")]
cols = (0, 9, 66, 78); anchos = (9, 57, 12, 66)
for i, f in enumerate(filas):
    y = ly - i * 6.2
    for (c, w), t in zip(zip(cols, anchos), f):
        rect(lx + c, y - 6.2, w, 6.2, lw=.5)
        ax.text(lx + c + 1.5, y - 3.1, t, va="center", fontsize=6.8, weight="bold" if i == 0 else None)

# ---------------- CAJETÍN ----------------
bx, by, bw = 222, 5, 70
for i, (k, v) in enumerate([("Proyecto", "FruitAI"), ("Plano", "Estación de registro"), ("Escala", "1:5 (lámina A4)"),
                            ("Unidades", "mm"), ("Material", "MDF 5 mm / cartón")]):
    rect(bx, by + i * 6, bw, 6, lw=.6); ax.text(bx + 1.5, by + i * 6 + 3, k, va="center", fontsize=6.5, color=G)
    ax.text(bx + 20, by + i * 6 + 3, v, va="center", fontsize=7, weight="bold" if k == "Plano" else None)
ax.text(222, 40, "Cotas aproximadas; lo importante es\nque la cámara y la luz no se muevan entre\nla captura del dataset y el uso.",
        ha="left", fontsize=6.5, style="italic", color=G)
fig.savefig("plano_estacion.png", dpi=220); print("ok")
