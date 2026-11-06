"""Inventario de FruitAI sobre SQLite.

Única fuente de verdad: la tabla `movimientos`. El stock no se guarda, se
calcula. Este módulo no sabe nada de MQTT, para poder probarlo solo.
"""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ESQUEMA = """
CREATE TABLE IF NOT EXISTS frutas (
  id INTEGER PRIMARY KEY,
  nombre TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS movimientos (
  id INTEGER PRIMARY KEY,
  fruta_id INTEGER NOT NULL REFERENCES frutas(id),
  tipo TEXT NOT NULL CHECK (tipo IN ('entrada','salida')),
  cantidad INTEGER NOT NULL DEFAULT 1 CHECK (cantidad > 0),
  confianza REAL,            -- confianza del modelo TinyML
  fecha TEXT NOT NULL,       -- ISO 8601 con zona horaria
  evento_id TEXT UNIQUE      -- id del evento enviado por el ESP32 (evita duplicados de MQTT QoS 1)
);
CREATE INDEX IF NOT EXISTS idx_mov_fruta_fecha ON movimientos(fruta_id, fecha);

CREATE TABLE IF NOT EXISTS lecturas_ambiente (
  id INTEGER PRIMARY KEY,
  temperatura REAL,
  humedad REAL,
  fecha TEXT NOT NULL
);
"""

TIPOS = ("entrada", "salida")


@dataclass
class Resultado:
    ok: bool
    fruta: str | None = None
    aviso: str | None = None
    duplicado: bool = False


class Inventario:
    def __init__(self, ruta: str, frutas: list[str], zona: str = "America/Bogota"):
        self.zona = ZoneInfo(zona)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(ruta, check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript(ESQUEMA)
        with self._conn:
            self._conn.executemany(
                "INSERT OR IGNORE INTO frutas(nombre) VALUES (?)",
                [(f.strip().lower(),) for f in frutas if f.strip()],
            )

    # ---------- utilidades ----------
    def ahora(self) -> datetime:
        return datetime.now(self.zona)

    def _iso(self, momento: datetime | None) -> str:
        momento = momento or self.ahora()
        if momento.tzinfo is None:
            momento = momento.replace(tzinfo=self.zona)
        return momento.isoformat(timespec="seconds")

    def frutas(self) -> list[str]:
        with self._lock:
            filas = self._conn.execute("SELECT nombre FROM frutas ORDER BY id").fetchall()
        return [f[0] for f in filas]

    # ---------- consultas ----------
    def stock(self) -> dict[str, int]:
        with self._lock:
            return self._stock_sin_lock()

    def _stock_sin_lock(self) -> dict[str, int]:
        filas = self._conn.execute(
            """
            SELECT f.nombre,
                   COALESCE(SUM(CASE WHEN m.tipo = 'entrada' THEN m.cantidad
                                     ELSE -m.cantidad END), 0) AS stock
            FROM frutas f
            LEFT JOIN movimientos m ON m.fruta_id = f.id
            GROUP BY f.id
            ORDER BY f.id
            """
        ).fetchall()
        return {nombre: stock for nombre, stock in filas}

    def salidas_desde(self, fruta: str, desde: datetime) -> int:
        # datetime() de SQLite normaliza a UTC, así la comparación es correcta
        # aunque las fechas tengan zona horaria.
        with self._lock:
            (total,) = self._conn.execute(
                """
                SELECT COALESCE(SUM(m.cantidad), 0)
                FROM movimientos m JOIN frutas f ON f.id = m.fruta_id
                WHERE f.nombre = ? AND m.tipo = 'salida'
                  AND datetime(m.fecha) >= datetime(?)
                """,
                (fruta, self._iso(desde)),
            ).fetchone()
        return total

    def resumen(self, fruta: str, ahora: datetime | None = None) -> dict[str, int]:
        ahora = ahora or self.ahora()
        inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        inicio_semana = inicio_dia - timedelta(days=inicio_dia.weekday())  # lunes
        return {
            "salidas_hoy": self.salidas_desde(fruta, inicio_dia),
            "salidas_semana": self.salidas_desde(fruta, inicio_semana),
        }

    # ---------- escrituras ----------
    def registrar_movimiento(
        self,
        fruta,
        tipo,
        cantidad=1,
        confianza=None,
        evento_id=None,
        fecha: datetime | None = None,
    ) -> Resultado:
        if not isinstance(fruta, str) or not fruta.strip():
            return Resultado(False, aviso="Movimiento sin fruta: ignorado")
        fruta = fruta.strip().lower()
        if tipo not in TIPOS:
            return Resultado(False, fruta, f"Tipo de movimiento inválido: {tipo!r}")
        if isinstance(cantidad, bool) or not isinstance(cantidad, int) or cantidad < 1:
            return Resultado(False, fruta, f"Cantidad inválida: {cantidad!r}")
        if confianza is not None:
            if isinstance(confianza, bool) or not isinstance(confianza, (int, float)) or not 0 <= confianza <= 1:
                return Resultado(False, fruta, f"Confianza inválida: {confianza!r}")

        with self._lock:
            fila = self._conn.execute("SELECT id FROM frutas WHERE nombre = ?", (fruta,)).fetchone()
            if fila is None:
                return Resultado(False, fruta, f"Fruta desconocida: {fruta}")
            if evento_id is not None:
                repetido = self._conn.execute(
                    "SELECT 1 FROM movimientos WHERE evento_id = ?", (str(evento_id),)
                ).fetchone()
                if repetido:
                    return Resultado(False, fruta, duplicado=True)
            if tipo == "salida":
                actual = self._stock_sin_lock()[fruta]
                if actual < cantidad:
                    return Resultado(
                        False, fruta, f"Salida de {fruta} rechazada: stock {actual}"
                    )
            with self._conn:
                self._conn.execute(
                    """INSERT INTO movimientos(fruta_id, tipo, cantidad, confianza, fecha, evento_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (fila[0], tipo, cantidad, confianza, self._iso(fecha),
                     None if evento_id is None else str(evento_id)),
                )
        return Resultado(True, fruta)

    def registrar_ambiente(self, temperatura, humedad, fecha: datetime | None = None) -> bool:
        for valor in (temperatura, humedad):
            if valor is not None and (isinstance(valor, bool) or not isinstance(valor, (int, float))):
                return False
        if temperatura is None and humedad is None:
            return False
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO lecturas_ambiente(temperatura, humedad, fecha) VALUES (?, ?, ?)",
                (temperatura, humedad, self._iso(fecha)),
            )
        return True
