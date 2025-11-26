"""Backup bot_db.sqlite and tg_db.sqlite into backup_db/ with timestamped filenames."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import sys


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_db_path(preferred: Path, fallback_candidates: list[Path]) -> Path:
    if preferred.exists():
        return preferred
    for candidate in fallback_candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Source database not found. Tried: {[str(p) for p in [preferred, *fallback_candidates]]}"
    )


def unique_backup_path(base_dir: Path, prefix: str, timestamp: str) -> Path:
    candidate = base_dir / f"{prefix}_{timestamp}.sqlite"
    if not candidate.exists():
        return candidate

    counter = 1
    while True:
        candidate = base_dir / f"{prefix}_{timestamp}_{counter}.sqlite"
        if not candidate.exists():
            return candidate
        counter += 1


def backup_database(src: Path, backup_dir: Path, prefix: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    dest = unique_backup_path(backup_dir, prefix, timestamp)
    shutil.copy2(src, dest)
    return dest


def main() -> None:
    root = get_project_root()
    data_dir = root / "data"
    backup_dir = root / "backup_db"
    backup_dir.mkdir(parents=True, exist_ok=True)

    sources: dict[str, Path] = {}
    sources["bot_db"] = resolve_db_path(
        data_dir / "bot_db.sqlite",
        [data_dir / "bot.db", root / "bot.db", root / "tg_bot.db"],
    )
    sources["tg_db"] = resolve_db_path(
        data_dir / "tg_db.sqlite",
        [data_dir / "tg_bot.db", root / "tg_bot.db"],
    )

    backups = {}
    for prefix, path in sources.items():
        try:
            backups[prefix] = backup_database(path, backup_dir, prefix)
        except FileNotFoundError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            raise

    for prefix, backup_path in backups.items():
        print(f"[OK] {prefix} backup created: {backup_path}")


if __name__ == "__main__":
    main()
