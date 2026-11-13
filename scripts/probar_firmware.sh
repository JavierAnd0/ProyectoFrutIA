#!/usr/bin/env bash
# Prueba en el PC la lógica anti-duplicados del firmware (confirmacion.h), con
# los mismos casos que simulador/tests/test_confirmacion.py. Necesita g++ o clang++
# (en el Mac: xcode-select --install).
set -euo pipefail
cd "$(dirname "$0")/../firmware/fruitai_camara/test"
CXX="${CXX:-$(command -v g++ || command -v clang++)}"
salida="$(mktemp)"
"$CXX" -std=c++17 -Wall -Wextra -Werror -I.. test_confirmacion.cpp -o "$salida"
"$salida"
rm -f "$salida"
