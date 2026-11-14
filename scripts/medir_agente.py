"""Mide los agentes de conversación de FruitAI (sección 9.3 y 10 del documento).

Hace las mismas preguntas a cada agente por la API de Home Assistant, toma el
tiempo de cada respuesta y comprueba si contiene el número correcto (leído de
los sensores en ese momento). Guarda una tabla en docs/resultados/.

Requisitos: HA_TOKEN en .env (token de larga duración de Home Assistant).
Solo usa la biblioteca estándar: corre igual en el Mac y en la Raspberry Pi.

  python scripts/medir_agente.py                       # todos los agentes "fruitai" + el local
  python scripts/medir_agente.py --repeticiones 3
  python scripts/medir_agente.py --agentes conversation.fruitai_qwen2_5_3b
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import statistics
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

FRUTAS = ["manzana", "pera", "banano", "kiwi"]
SINONIMOS = {"banano": ["banano", "banana", "plátano", "platano"], "manzana": ["manzana"],
             "pera": ["pera"], "kiwi": ["kiwi"]}


def _num(estados: dict, sensor: str) -> float:
    try:
        return float(estados.get(sensor, "nan"))
    except ValueError:
        return float("nan")


def _sensor(sensor: str):
    return lambda e: ("numero", [e.get(sensor, "?")])


def _extremo(prefijo: str, func):
    """Fruta(s) con el valor mínimo o máximo del sensor (en un empate vale cualquiera)."""
    def calcular(e):
        valores = {f: _num(e, f"sensor.fruitai_{prefijo}_{f}") for f in FRUTAS}
        objetivo = func(valores.values())
        return ("fruta", [f for f, v in valores.items() if v == objetivo])
    return calcular


def _total(e):
    return ("numero", [str(int(sum(_num(e, f"sensor.fruitai_stock_{f}") for f in FRUTAS)))])


# (pregunta, cómo calcular la respuesta correcta desde los sensores, ¿abierta?)
# "Abierta" = no la cubren las oraciones locales: es el trabajo del agente de Ollama.
PREGUNTAS = [
    ("¿Cuántas peras hay?", _sensor("sensor.fruitai_stock_pera"), False),
    ("¿Me quedan manzanas? ¿Cuántas?", _sensor("sensor.fruitai_stock_manzana"), False),
    ("¿Cuántos bananos salieron esta semana?", _sensor("sensor.fruitai_salidas_semana_banano"), False),
    ("¿Cuántas manzanas se consumieron esta semana?", _sensor("sensor.fruitai_salidas_semana_manzana"), False),
    ("¿A qué temperatura está el frutero?", _sensor("sensor.fruitai_temperatura_frutero"), False),
    ("¿Qué fruta se está acabando?", _extremo("stock", min), True),
    ("¿De qué fruta tengo más?", _extremo("stock", max), True),
    ("¿Cuántas frutas hay en total?", _total, True),
    ("¿Qué fruta se comió más esta semana?", _extremo("salidas_semana", max), True),
]

AGENTE_LOCAL = "conversation.home_assistant"  # agente integrado: oraciones locales, sin LLM

NUMEROS = {
    "cero": 0, "ninguno": 0, "ninguna": 0, "no hay": 0, "un": 1, "uno": 1, "una": 1,
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
    "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
    "quince": 15, "veinte": 20,
}


def leer_env() -> dict[str, str]:
    env = {}
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text().splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                env[k.strip()] = v.strip()
    return env


class HA:
    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/")
        self.token = token

    def _pedir(self, metodo: str, ruta: str, cuerpo=None, timeout=180):
        datos = None if cuerpo is None else json.dumps(cuerpo).encode()
        req = urllib.request.Request(
            self.url + ruta, data=datos, method=metodo,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def estados(self) -> dict[str, str]:
        return {e["entity_id"]: e["state"] for e in self._pedir("GET", "/api/states")}

    def preguntar(self, texto: str, agente: str) -> str:
        r = self._pedir("POST", "/api/conversation/process",
                        {"text": texto, "language": "es", "agent_id": agente})
        return r["response"]["speech"]["plain"]["speech"]


def numeros_en(texto: str) -> set[float]:
    t = texto.lower()
    encontrados = {float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", t)}
    for palabra, valor in NUMEROS.items():
        if re.search(rf"\b{palabra}\b", t):
            encontrados.add(float(valor))
    return encontrados


def es_correcta(respuesta: str, tipo: str, valores: list[str]) -> bool:
    if tipo == "fruta":   # basta con que nombre una de las frutas correctas
        t = respuesta.lower()
        return any(re.search(rf"\b{s}s?\b", t) for f in valores for s in SINONIMOS[f])
    try:
        valor = float(valores[0])
    except ValueError:
        return False
    return any(abs(n - valor) < 0.05 for n in numeros_en(respuesta))


def ram_ollama() -> str:
    try:
        salida = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", "fruitai-ollama"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        return salida.split("/")[0].strip() or "?"
    except (OSError, subprocess.SubprocessError):
        return "?"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8123")
    ap.add_argument("--agentes", nargs="*", help="entity_id de los agentes (por defecto: todos los fruitai + local)")
    ap.add_argument("--repeticiones", type=int, default=2)
    ap.add_argument("--equipo", default=f"{platform.node()} ({platform.machine()})",
                    help="cómo se llama el equipo en el informe (ej. 'Raspberry Pi 5 8 GB')")
    args = ap.parse_args()

    token = leer_env().get("HA_TOKEN")
    if not token:
        raise SystemExit("Falta HA_TOKEN en .env (perfil de HA → Seguridad → Tokens de larga duración)")
    ha = HA(args.url, token)

    estados = ha.estados()
    agentes = args.agentes or sorted(
        e for e in estados if e.startswith("conversation.") and "fruitai" in e
    ) + [AGENTE_LOCAL]
    print(f"Agentes: {', '.join(agentes)}\n")

    filas_resumen, detalle = [], []
    for agente in agentes:
        es_llm = agente != AGENTE_LOCAL
        if es_llm:  # calentamiento: la primera llamada incluye cargar el modelo
            print(f"[{agente}] cargando modelo…", flush=True)
            t0 = time.perf_counter()
            ha.preguntar("Hola", agente)
            print(f"  carga inicial: {time.perf_counter() - t0:.1f} s")

        tiempos, aciertos, total = [], 0, 0
        aciertos_tipo = {False: [0, 0], True: [0, 0]}
        for pregunta, calcular, abierta in PREGUNTAS:
            for i in range(args.repeticiones):
                tipo, valores = calcular(ha.estados())
                esperado = " o ".join(valores)
                t0 = time.perf_counter()
                try:
                    respuesta = ha.preguntar(pregunta, agente)
                except Exception as e:  # noqa: BLE001 — se registra y se sigue
                    respuesta = f"ERROR: {e}"
                seg = time.perf_counter() - t0
                ok = es_correcta(respuesta, tipo, valores)
                tiempos.append(seg)
                aciertos += ok
                total += 1
                aciertos_tipo[abierta][0] += ok
                aciertos_tipo[abierta][1] += 1
                detalle.append((agente, pregunta + (" (abierta)" if abierta else ""), esperado, respuesta.replace("\n", " "), f"{seg:.1f}", "sí" if ok else "no"))
                print(f"  {'✓' if ok else '✗'} {seg:5.1f} s  {pregunta}  → {respuesta[:90]}  (esperado {esperado})")

        ram = ram_ollama() if es_llm else "—"
        cerr, abie = aciertos_tipo[False], aciertos_tipo[True]
        filas_resumen.append((agente, ram, f"{statistics.mean(tiempos):.1f}",
                              f"{statistics.median(tiempos):.1f}", f"{max(tiempos):.1f}",
                              f"{cerr[0]}/{cerr[1]}", f"{abie[0]}/{abie[1]}"))
        print()

    # ---------- informe ----------
    ahora = datetime.now()
    salida = RAIZ / "docs" / "resultados" / f"agente_{ahora:%Y%m%d_%H%M}.md"
    salida.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        f"# Medición del agente — {ahora:%Y-%m-%d %H:%M}",
        "",
        f"- Equipo: {args.equipo}",
        f"- Repeticiones por pregunta: {args.repeticiones} (sin contar la carga inicial del modelo)",
        "- Correcta = la respuesta contiene el valor del sensor en ese momento, o nombra la fruta correcta "
        "(revisar el detalle a mano).",
        "- Comunes = las cubren las oraciones locales. Abiertas = solo las puede responder el agente de Ollama.",
        "",
        "| Agente | RAM Ollama | Tiempo medio (s) | Mediana (s) | Máximo (s) | Comunes | Abiertas |",
        "|---|---|---|---|---|---|---|",
        *[f"| {' | '.join(f)} |" for f in filas_resumen],
        "",
        "## Detalle",
        "",
        "| Agente | Pregunta | Esperado | Respuesta | Tiempo (s) | ¿Correcta? |",
        "|---|---|---|---|---|---|",
        *[f"| {' | '.join(c.replace('|', '/') for c in f)} |" for f in detalle],
        "",
    ]
    salida.write_text("\n".join(lineas))
    print("\n".join(lineas[7:7 + 2 + len(filas_resumen)]))
    print(f"\nInforme: {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
