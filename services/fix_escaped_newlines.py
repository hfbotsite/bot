from __future__ import annotations

from pathlib import Path

FILES = [
    "services/bot_engine/fill_handler.py",
    "services/bot_engine/fills_repo.py",
    "services/bot_engine/positions_repo.py",
]


def fix_file(path: str) -> None:
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    p.write_text(s.encode("utf-8").decode("unicode_escape"), encoding="utf-8")


def main() -> None:
    for f in FILES:
        fix_file(f)
        print("fixed", f)


if __name__ == "__main__":
    main()

