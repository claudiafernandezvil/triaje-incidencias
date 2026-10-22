"""Acceso a la base de datos SQLite del servicio de soporte.
 
La base de datos contiene dos tablas:
- incidencias_resueltas: el historial de incidencias resueltas (con su solución).
- tickets: las incidencias registradas por el sistema (abiertas o cerradas).
 
La ruta se configura con la variable de entorno RUTA_BD (por defecto
data/soporte.db) y se lee en cada conexión, de modo que los tests y las
evaluaciones pueden usar una base de datos aparte.
 
La primera vez que se usa, la base de datos se crea sola:
- se crean las tablas si no existen;
- si el historial está vacío, se cargan las incidencias del CSV inicial;
- si la tabla de tickets está vacía y existe el CSV de tickets de la versión
  anterior, se importan esos tickets.
"""
 
from __future__ import annotations
 
import csv
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
 
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_BD_POR_DEFECTO = RAIZ_PROYECTO / "data" / "soporte.db"
 
# Datos iniciales del historial (se usa el primero que exista)
CSV_HISTORIAL_INICIAL = (
    RAIZ_PROYECTO / "data" / "incidencias_resueltas.csv",
    RAIZ_PROYECTO / "data" / "incidencias.csv",
)
# Tickets de la versión anterior (basada en CSV), para no perderlos
CSV_TICKETS_ANTERIOR = RAIZ_PROYECTO / "data" / "tickets_registrados.csv"
 
ESQUEMA = """
CREATE TABLE IF NOT EXISTS incidencias_resueltas (
    id               TEXT PRIMARY KEY,
    descripcion      TEXT NOT NULL,
    categoria        TEXT NOT NULL,
    impacto          TEXT,
    urgencia         TEXT,
    solucion         TEXT NOT NULL,
    origen           TEXT NOT NULL DEFAULT 'historial',
    fecha_resolucion TEXT
);
 
CREATE TABLE IF NOT EXISTS tickets (
    id           TEXT PRIMARY KEY,
    fecha        TEXT NOT NULL,
    descripcion  TEXT NOT NULL,
    categoria    TEXT NOT NULL,
    impacto      TEXT NOT NULL,
    urgencia     TEXT NOT NULL,
    prioridad    TEXT NOT NULL,
    estado       TEXT NOT NULL DEFAULT 'abierta',
    fecha_cierre TEXT,
    solucion     TEXT
);
 
CREATE INDEX IF NOT EXISTS idx_resueltas_categoria ON incidencias_resueltas (categoria);
CREATE INDEX IF NOT EXISTS idx_tickets_estado ON tickets (estado);
"""
 
 
def ruta_bd() -> Path:
    """Devuelve la ruta de la base de datos (configurable con RUTA_BD)."""
    return Path(os.getenv("RUTA_BD", str(RUTA_BD_POR_DEFECTO)))
 
 
@contextmanager
def conectar() -> Iterator[sqlite3.Connection]:
    """Abre una conexión a la base de datos, la inicializa si hace falta y la cierra al terminar.
 
    Si todo va bien, guarda los cambios (commit); si hay un error, los deshace (rollback).
    """
    ruta = ruta_bd()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    try:
        _inicializar(conexion)
        yield conexion
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()
 
 
def _inicializar(conexion: sqlite3.Connection) -> None:
    conexion.executescript(ESQUEMA)
    if conexion.execute("SELECT COUNT(*) FROM incidencias_resueltas").fetchone()[0] == 0:
        _cargar_historial_inicial(conexion)
    if conexion.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 0:
        _importar_tickets_anteriores(conexion)
    conexion.commit()
 
 
def _cargar_historial_inicial(conexion: sqlite3.Connection) -> None:
    ruta = next((r for r in CSV_HISTORIAL_INICIAL if r.exists()), None)
    if ruta is None:
        return
    with open(ruta, encoding="utf-8", newline="") as f:
        filas = [
            (
                fila["id"],
                fila["descripcion"],
                fila["categoria"],
                fila.get("impacto"),
                fila.get("urgencia"),
                fila["solucion"],
            )
            for fila in csv.DictReader(f)
        ]
    conexion.executemany(
        "INSERT OR IGNORE INTO incidencias_resueltas "
        "(id, descripcion, categoria, impacto, urgencia, solucion, origen) "
        "VALUES (?, ?, ?, ?, ?, ?, 'historial')",
        filas,
    )
 
 
def _importar_tickets_anteriores(conexion: sqlite3.Connection) -> None:
    # Solo se importan con la base de datos por defecto, no en tests ni evaluaciones
    if ruta_bd() != RUTA_BD_POR_DEFECTO or not CSV_TICKETS_ANTERIOR.exists():
        return
    with open(CSV_TICKETS_ANTERIOR, encoding="utf-8", newline="") as f:
        filas = [
            (
                fila["id"],
                fila["fecha"],
                fila["descripcion"],
                fila["categoria"],
                fila["impacto"],
                fila["urgencia"],
                fila["prioridad"],
                fila.get("estado") or "abierta",
            )
            for fila in csv.DictReader(f)
        ]
    conexion.executemany(
        "INSERT OR IGNORE INTO tickets "
        "(id, fecha, descripcion, categoria, impacto, urgencia, prioridad, estado) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        filas,
    )