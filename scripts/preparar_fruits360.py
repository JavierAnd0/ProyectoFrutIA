"""Toma una muestra de Fruits-360 y la agrega a dataset/ con las clases de FruitAI.

Fruits-360 (Mihai Oltean, CC BY-SA 4.0): https://github.com/fruits-360/fruits-360-100x100
Solo se descargan las carpetas de nuestras frutas (sparse checkout, ~150 MB):

  git clone --depth 1 --filter=blob:none --sparse https://github.com/fruits-360/fruits-360-100x100.git /tmp/f360
  python scripts/preparar_fruits360.py --repo /tmp/f360 --imprimir-patrones | git -C /tmp/f360 sparse-checkout set --no-cone --stdin
  python scripts/preparar_fruits360.py --repo /tmp/f360 --por-clase 150

Las fotos quedan como dataset/<clase>/<clase>.f360-<variedad>-<n>.jpg; Edge Impulse
toma la etiqueta de lo que va antes del primer punto. El prefijo "f360" permite
distinguirlas (o borrarlas) de las fotos propias.

Ojo: Fruits-360 son frutas girando sobre fondo blanco con luz fija. Sirven de
base, pero el modelo necesita además fotos del montaje real y la clase "fondo"
(simulador/capturar_dataset.py).
"""
from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# clase de FruitAI → variedades de Fruits-360. Se excluyen las manzanas amarillas
# (Golden) o bicolor y las numeradas sin nombre, para no confundir rojas/verdes,
# y el banano rojo.
VARIEDADES = {
    "manzana_roja": ["Apple Red 1", "Apple Red 2", "Apple Red 3", "Apple Red Delicious 1",
                     "Apple Braeburn 1", "Apple Pink Lady 1", "Apple Crimson Snow 1"],
    "manzana_verde": ["Apple Granny Smith 1"],
    # sin "Pear Kaiser 1": es marrón oscura y se confunde con el kiwi
    "pera": ["Pear 1", "Pear 2", "Pear 3", "Pear Williams 1", "Pear Abate 1"],
    "banano": ["Banana 1", "Banana 2", "Banana 3", "Banana 4", "Banana Lady Finger 1"],
    "kiwi": ["Kiwi 1", "Kiwi 2", "Kiwi 3"],
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, required=True, help="clon de fruits-360-100x100")
    ap.add_argument("--salida", type=Path, default=RAIZ / "dataset")
    ap.add_argument("--por-clase", type=int, default=150)
    ap.add_argument("--semilla", type=int, default=360)
    ap.add_argument("--imprimir-patrones", action="store_true", help="patrones para git sparse-checkout")
    args = ap.parse_args()

    if args.imprimir_patrones:
        for variedades in VARIEDADES.values():
            for v in variedades:
                print(f"/Training/{v}/\n/Test/{v}/")
        return

    azar = random.Random(args.semilla)
    for clase, variedades in VARIEDADES.items():
        destino = args.salida / clase
        destino.mkdir(parents=True, exist_ok=True)
        for viejo in destino.glob(f"{clase}.f360-*.jpg"):     # rehacer la muestra sin duplicar
            viejo.unlink()
        # reparto parejo entre variedades; Training y Test juntos (Edge Impulse
        # hace su propia división entrenamiento/prueba)
        cuota = [args.por_clase // len(variedades)] * len(variedades)
        for i in range(args.por_clase % len(variedades)):
            cuota[i] += 1
        total = 0
        for variedad, n in zip(variedades, cuota):
            fotos = sorted(p for parte in ("Training", "Test") for p in (args.repo / parte / variedad).glob("*.jpg"))
            if not fotos:
                raise SystemExit(f"No hay fotos de {variedad!r} en {args.repo}. ¿Faltó el sparse-checkout?")
            nombre = variedad.lower().replace(" ", "_")
            for j, foto in enumerate(azar.sample(fotos, min(n, len(fotos)))):
                shutil.copyfile(foto, destino / f"{clase}.f360-{nombre}-{j}.jpg")
                total += 1
        print(f"{clase:14s} {total:4d} fotos de {len(variedades)} variedad(es)")
    print(f"Listo en {args.salida}. Falta: fotos propias de cada fruta y la clase 'fondo'.")


if __name__ == "__main__":
    main()
