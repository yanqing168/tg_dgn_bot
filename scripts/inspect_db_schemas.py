"""Inspect schema definitions of bot_db.sqlite and tg_db.sqlite."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_db_path(preferred: Path, fallbacks: List[Path]) -> Path:
    if preferred.exists():
        return preferred
    for candidate in fallbacks:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Database not found. Tried: {[str(p) for p in [preferred, *fallbacks]]}"
    )


def open_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_tables(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    cursor = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return cursor.fetchall()


def fetch_table_info(conn: sqlite3.Connection, table_name: str) -> List[sqlite3.Row]:
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()


def print_schema(label: str, tables: List[sqlite3.Row], conn: sqlite3.Connection) -> None:
    print(f"=== {label} tables ===")
    if not tables:
        print("(no tables)")
        return

    for table in tables:
        name = table["name"]
        sql = table["sql"]
        print(f"\n-- {name} --")
        print(sql)
        cols = fetch_table_info(conn, name)
        for col in cols:
            print(
                f"    column: {col['name']} | type: {col['type']} | notnull: {col['notnull']} | default: {col['dflt_value']} | pk: {col['pk']}"
            )


def main() -> None:
    root = get_project_root()
    data_dir = root / "data"

    bot_db = resolve_db_path(data_dir / "bot_db.sqlite", [data_dir / "bot.db", root / "bot.db"])
    tg_db = resolve_db_path(data_dir / "tg_db.sqlite", [data_dir / "tg_bot.db", root / "tg_bot.db"])

    dbs: Dict[str, Path] = {"bot_db": bot_db, "tg_db": tg_db}

    schema_cache: Dict[str, List[str]] = {}
    for label, path in dbs.items():
        print(f"\n=== Inspecting {label}: {path} ===")
        conn = open_connection(path)
        tables = fetch_tables(conn)
        schema_cache[label] = [table["name"] for table in tables]
        print_schema(label, tables, conn)
        conn.close()

    bot_tables = set(schema_cache["bot_db"])
    tg_tables = set(schema_cache["tg_db"])

    print("\n=== Summary ===")
    print("Only in bot_db:", sorted(bot_tables - tg_tables))
    print("Only in tg_db:", sorted(tg_tables - bot_tables))
    print("Common tables:", sorted(bot_tables & tg_tables))


if __name__ == "__main__":
    main()
