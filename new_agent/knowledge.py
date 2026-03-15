from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Iterable


def _candidate_paths() -> Iterable[Path]:
    env_path = os.getenv("OFSTRIDE_KNOWLEDGE_PATH") or os.getenv("KNOWLEDGE_PATH")
    if env_path:
        yield Path(env_path)

    base_dir = Path(__file__).resolve().parent
    yield base_dir / "knowledge" / "ofstride_services.txt"

    repo_root = base_dir
    for _ in range(6):
        if (repo_root / "data" / "knowledge").exists():
            yield repo_root / "data" / "knowledge" / "ofstride_services.txt"
            break
        if repo_root.parent == repo_root:
            break
        repo_root = repo_root.parent


@lru_cache
def load_knowledge(path_override: str | None = None) -> str:
    if path_override:
        try:
            path = Path(path_override)
            if path.is_file():
                return path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    for path in _candidate_paths():
        try:
            if path.is_file():
                return path.read_text(encoding="utf-8").strip()
        except Exception:
            continue
    return ""
