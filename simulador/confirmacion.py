"""Lógica de confirmación anti-duplicados del ESP32 (plan v4, día 9).

Es la misma lógica que llevará el firmware. Está escrita sin dependencias y con
estados simples para pasarla a C++ casi línea por línea.

Problema que resuelve: la cámara predice ~5 veces por segundo y la misma fruta
sigue visible durante muchos fotogramas. El inventario NO debe cambiar con cada
predicción. Reglas:

1. Una fruta queda CONFIRMADA cuando el modelo la predice `frames_confirmar`
   fotogramas seguidos con confianza >= `umbral` (y hay presencia).
2. Solo con una fruta confirmada, un botón (entrada/salida) genera UN movimiento.
3. Después del movimiento la fruta queda REGISTRADA: más pulsaciones se ignoran
   hasta que la fruta se retire (`frames_retiro` fotogramas de "fondo" o sin
   presencia). Así no se duplica un registro por pulsar dos veces.

Estados: ESPERANDO → CONFIRMADA → (botón) → REGISTRADA → (retiro) → ESPERANDO
"""
from __future__ import annotations

from dataclasses import dataclass

ESPERANDO = "ESPERANDO"
CONFIRMADA = "CONFIRMADA"
REGISTRADA = "REGISTRADA"

# Clases del modelo que se registran como la misma fruta del inventario.
MAPA_POR_DEFECTO = {"manzana_roja": "manzana", "manzana_verde": "manzana"}


@dataclass
class Movimiento:
    fruta: str
    tipo: str        # "entrada" | "salida"
    confianza: float


class Confirmador:
    def __init__(
        self,
        umbral: float = 0.75,
        frames_confirmar: int = 5,
        frames_retiro: int = 5,
        fondo: str = "fondo",
        mapa: dict[str, str] | None = None,
    ):
        self.umbral = umbral
        self.frames_confirmar = frames_confirmar
        self.frames_retiro = frames_retiro
        self.fondo = fondo
        self.mapa = MAPA_POR_DEFECTO if mapa is None else mapa

        self.estado = ESPERANDO
        self.fruta: str | None = None       # fruta confirmada / registrada
        self.confianza = 0.0                # media de los fotogramas que la confirmaron
        self.mensaje = ""                   # última explicación (para pantalla / serial)
        self._candidata: str | None = None
        self._seguidos = 0
        self._suma_conf = 0.0
        self._ausente = 0

    def _a_fruta(self, etiqueta: str) -> str:
        return self.mapa.get(etiqueta, etiqueta)

    def _reiniciar_candidata(self) -> None:
        self._candidata, self._seguidos, self._suma_conf = None, 0, 0.0

    def procesar(self, etiqueta: str, confianza: float, presencia: bool = True) -> str:
        """Recibe la predicción de un fotograma. Devuelve el estado resultante."""
        hay_fruta = presencia and etiqueta != self.fondo and confianza >= self.umbral
        fruta = self._a_fruta(etiqueta) if hay_fruta else None

        # ¿Se retiró la fruta confirmada/registrada?
        if self.estado in (CONFIRMADA, REGISTRADA):
            ausente = (not presencia) or etiqueta == self.fondo
            self._ausente = self._ausente + 1 if ausente else 0
            if self._ausente >= self.frames_retiro:
                self.mensaje = f"{self.fruta} retirada"
                self.estado, self.fruta, self.confianza, self._ausente = ESPERANDO, None, 0.0, 0
                self._reiniciar_candidata()
                return self.estado
            if self.estado == REGISTRADA or fruta in (None, self.fruta):
                return self.estado
            # CONFIRMADA y ahora se ve otra fruta con buena confianza: se
            # cuenta como candidata nueva (cambio de fruta sin pasar por fondo).

        if fruta is None:
            self._reiniciar_candidata()
            return self.estado

        if fruta == self._candidata:
            self._seguidos += 1
            self._suma_conf += confianza
        else:
            self._candidata, self._seguidos, self._suma_conf = fruta, 1, confianza

        if self._seguidos >= self.frames_confirmar:
            self.estado = CONFIRMADA
            self.fruta = fruta
            self.confianza = round(self._suma_conf / self._seguidos, 2)
            self._ausente = 0
            self._reiniciar_candidata()
            self.mensaje = f"{fruta} confirmada ({self.confianza:.0%}). Pulsa entrada o salida"
        return self.estado

    def boton(self, tipo: str) -> Movimiento | None:
        """Pulsación de un botón. Devuelve el movimiento a publicar, o None."""
        if tipo not in ("entrada", "salida"):
            raise ValueError(tipo)
        if self.estado == ESPERANDO:
            self.mensaje = "Ignorado: no hay una fruta confirmada"
            return None
        if self.estado == REGISTRADA:
            self.mensaje = f"Ignorado: {self.fruta} ya se registró; retírala antes de otro registro"
            return None
        mov = Movimiento(self.fruta, tipo, self.confianza)
        self.estado = REGISTRADA
        self.mensaje = f"Registrado: {tipo} de {self.fruta}"
        return mov
