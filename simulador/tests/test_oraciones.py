"""Las oraciones locales de Assist reconocen las preguntas típicas.

Usa hassil, el mismo motor con el que Home Assistant interpreta
custom_sentences/es/fruitai.yaml, así que no hace falta HA corriendo.
Las preguntas son las de scripts/medir_agente.py y otras frecuentes.
"""
from pathlib import Path

import pytest
import yaml

hassil = pytest.importorskip("hassil")

ORACIONES = Path(__file__).resolve().parents[2] / "homeassistant/custom_sentences/es/fruitai.yaml"
INTENTS = hassil.Intents.from_dict(yaml.safe_load(ORACIONES.read_text()))

CASOS = [
    ("¿Cuántas peras hay?", "FruitaiStock", {"fruta": "pera"}),
    ("¿Me quedan manzanas? ¿Cuántas?", "FruitaiStock", {"fruta": "manzana"}),
    ("¿Cuántas manzanas me quedan?", "FruitaiStock", {"fruta": "manzana"}),
    ("¿Quedan kiwis?", "FruitaiStock", {"fruta": "kiwi"}),
    ("¿Hay plátanos?", "FruitaiStock", {"fruta": "banano"}),
    ("¿Cuántos bananos salieron esta semana?", "FruitaiSalidas", {"fruta": "banano", "periodo": "semana"}),
    ("¿Cuántas manzanas se consumieron esta semana?", "FruitaiSalidas", {"fruta": "manzana", "periodo": "semana"}),
    ("Cuántas peras salieron hoy", "FruitaiSalidas", {"fruta": "pera", "periodo": "hoy"}),
    ("¿A qué temperatura está el frutero?", "FruitaiAmbiente", {}),
    ("¿Cuál es la humedad del frutero?", "FruitaiAmbiente", {}),
    ("¿Qué frutas hay?", "FruitaiInventario", {}),
]


@pytest.mark.parametrize("texto,intent,entidades", CASOS)
def test_oracion_reconocida(texto, intent, entidades):
    r = hassil.recognize(texto, INTENTS)
    assert r is not None, f"no se reconoce: {texto}"
    assert r.intent.name == intent
    assert {k: v.value for k, v in r.entities.items()} == entidades


def test_pregunta_abierta_pasa_al_agente():
    # Lo que no encaja en las oraciones debe llegar al agente de Ollama.
    assert hassil.recognize("¿Qué fruta se consume más los lunes?", INTENTS) is None
