import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
plt.rcParams["font.family"] = "DejaVu Sans"
fig, ax = plt.subplots(figsize=(13, 7.4)); ax.set_xlim(0, 13); ax.set_ylim(0, 7.4); ax.axis("off")
ax.set_title("Conexiones del ESP32-S3 (Freenove ESP32-S3 WROOM CAM)", fontsize=13, weight="bold")
ROJO, NEGRO, AMAR, AZUL, VERDE, NAR = "#d62728", "#222222", "#e6b800", "#1f77b4", "#2ca02c", "#ff7f0e"

# Placa
ax.add_patch(FancyBboxPatch((4.6, 1.0), 2.6, 5.4, boxstyle="round,pad=0.03", fc="#1f4f8a", ec="#0d2a4d", lw=2))
ax.text(5.9, 6.05, "ESP32-S3", ha="center", color="w", fontsize=12, weight="bold")
ax.add_patch(Rectangle((5.35, 4.7), 1.1, 1.0, fc="#111", ec="#000")); ax.add_patch(Circle((5.9, 5.2), .3, fc="#333", ec="#666"))
ax.text(5.9, 4.5, "cámara OV2640", ha="center", color="#cfe0ff", fontsize=8)
ax.add_patch(Rectangle((5.55, 0.85), .7, .3, fc="#bbb", ec="#555")); ax.text(5.9, 0.55, "USB-C (5 V)", ha="center", fontsize=8.5)
ax.add_patch(Circle((6.85, 1.6), .1, fc="#4da3ff", ec="#fff")); ax.text(6.85, 1.32, "LED\nGPIO2", ha="center", color="w", fontsize=6.5)
pines_izq = [("3V3", 3.9), ("GND", 3.4), ("GPIO14", 2.9), ("GPIO21", 2.4)]
pines_der = [("3V3", 3.9), ("GND", 3.4), ("GPIO1", 2.9), ("GPIO47", 2.4)]
for n, y in pines_izq:
    ax.add_patch(Circle((4.75, y), .07, fc="#d4af37")); ax.text(4.9, y, n, va="center", color="w", fontsize=8)
for n, y in pines_der:
    ax.add_patch(Circle((7.05, y), .07, fc="#d4af37")); ax.text(6.9, y, n, va="center", ha="right", color="w", fontsize=8)

def cable(xs, ys, c, lw=2.2): ax.plot(xs, ys, color=c, lw=lw, solid_capstyle="round", zorder=1)

# Botón ENTRADA
ax.add_patch(Rectangle((1.0, 4.2), .9, .9, fc="#ddd", ec="#555")); ax.add_patch(Circle((1.45, 4.65), .28, fc="#2e9e45"))
ax.text(1.45, 4.65, "+", ha="center", va="center", color="w", fontsize=14, weight="bold")
ax.text(1.45, 3.95, "Botón ENTRADA", ha="center", fontsize=9, weight="bold")
cable([1.9, 3.5, 3.5, 4.75], [4.8, 4.8, 2.9, 2.9], AZUL); cable([1.9, 3.2, 3.2, 4.75], [4.45, 4.45, 3.4, 3.4], NEGRO)
# Botón SALIDA
ax.add_patch(Rectangle((1.0, 1.5), .9, .9, fc="#ddd", ec="#555")); ax.add_patch(Circle((1.45, 1.95), .28, fc="#c0392b"))
ax.text(1.45, 1.95, "−", ha="center", va="center", color="w", fontsize=14, weight="bold")
ax.text(1.45, 1.25, "Botón SALIDA", ha="center", fontsize=9, weight="bold")
cable([1.9, 3.8, 3.8, 4.75], [2.1, 2.1, 2.4, 2.4], VERDE); cable([1.9, 3.2, 3.2], [1.8, 1.8, 3.4], NEGRO)
ax.text(2.55, 0.6, "Cada botón: una pata al GPIO y la otra a GND.\nNo lleva resistencia (el ESP32 usa la interna).", ha="center", fontsize=8.5, color="#333")

# PIR
ax.add_patch(Rectangle((10.0, 4.6), 1.3, 1.0, fc="#2d6a3e", ec="#163")); ax.add_patch(Circle((10.65, 5.1), .38, fc="#f7f7f7", ec="#999"))
ax.text(10.65, 5.8, "PIR AM312", ha="center", fontsize=9, weight="bold")
ax.text(11.45, 5.35, "VCC", fontsize=7.5); ax.text(11.45, 5.1, "OUT", fontsize=7.5); ax.text(11.45, 4.85, "GND", fontsize=7.5)
cable([7.05, 8.6, 8.6, 10.0], [3.9, 3.9, 5.35, 5.35], ROJO); cable([7.05, 9.0, 9.0, 10.0], [2.9, 2.9, 5.1, 5.1], NAR)
cable([7.05, 8.3, 8.3, 10.0], [3.4, 3.4, 4.85, 4.85], NEGRO)
# DHT22
ax.add_patch(Rectangle((10.1, 1.3), .9, 1.5, fc="#f2f2f2", ec="#555"))
for i in range(4): ax.plot([10.15, 10.95], [1.6 + i * .3] * 2, color="#bbb", lw=.8)
ax.text(10.55, 3.05, "DHT22", ha="center", fontsize=9, weight="bold")
ax.text(11.1, 2.5, "VCC", fontsize=7.5); ax.text(11.1, 2.1, "DATA", fontsize=7.5); ax.text(11.1, 1.7, "GND", fontsize=7.5)
cable([8.6, 8.6, 10.1], [3.9, 2.5, 2.5], ROJO); cable([7.05, 10.1], [2.4, 2.1], AMAR); cable([8.3, 8.3, 10.1], [3.4, 1.7, 1.7], NEGRO)
# resistencia de 10 kΩ entre DATA y VCC (vertical, junto al sensor)
ax.plot([9.6, 9.6], [2.15, 2.5], color="#7a6a2a", lw=1.4, zorder=3)
ax.add_patch(Rectangle((9.52, 2.22), .16, .2, fc="#d9c27a", ec="#7a6a2a", zorder=4))
ax.text(9.45, 2.32, "10 kΩ", ha="right", va="center", fontsize=7.5)
ax.text(10.55, 0.85, "Si el módulo ya trae la resistencia de 10 kΩ, no hace falta.", ha="center", fontsize=8, color="#333")

# Tabla resumen
filas = [("Pieza", "Pin del ESP32", "Notas"),
         ("Botón ENTRADA", "GPIO14 y GND", "sin resistencia"),
         ("Botón SALIDA", "GPIO21 y GND", "sin resistencia"),
         ("PIR (OUT)", "GPIO1", "VCC a 3V3 (AM312)"),
         ("DHT22 (DATA)", "GPIO47", "VCC a 3V3, 10 kΩ a 3V3"),
         ("LED", "GPIO2", "el de la placa")]
for i, (a, b, c) in enumerate(filas):
    y = 0.15 + (len(filas) - 1 - i) * 0.0
for i, f in enumerate(filas):
    y = 7.0 - i * 0.27
    for j, (t, x) in enumerate(zip(f, (0.3, 1.9, 3.15))):
        ax.text(x, y, t, fontsize=8, weight="bold" if i == 0 else None, va="center")
ax.plot([0.3, 4.4], [6.87, 6.87], color="#999", lw=.8)
ax.text(6.5, 0.15, "XIAO ESP32S3 Sense: ENTRADA D0, SALIDA D1, PIR D2, DHT22 D3, LED el de la placa (ver firmware/fruitai_camara/README.md)",
        ha="center", fontsize=8, style="italic", color="#444")
fig.tight_layout(); fig.savefig("conexiones.png", dpi=170); print("ok")
