"""Per-server settings: which channel the bot answers in, and whether answers are public.

Stored in config.json next to bot.py as {"<guild id>": {"channel": <channel id or null>, "public": false}}.
"""
from __future__ import annotations

import json
from pathlib import Path

FILE = Path(__file__).resolve().parent / "config.json"


def _load() -> dict:
    try:
        return json.loads(FILE.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def get(guild_id: int | None) -> dict:
    if guild_id is None:  # DMs
        return {"channel": None, "public": False}
    return _load().get(str(guild_id), {"channel": None, "public": False})


def set_channel(guild_id: int, channel_id: int | None) -> None:
    cfg = _load()
    entry = cfg.setdefault(str(guild_id), {"channel": None, "public": False})
    entry["channel"] = channel_id
    FILE.write_text(json.dumps(cfg, indent=2), "utf-8")


def set_public(guild_id: int, public: bool) -> None:
    cfg = _load()
    entry = cfg.setdefault(str(guild_id), {"channel": None, "public": False})
    entry["public"] = public
    FILE.write_text(json.dumps(cfg, indent=2), "utf-8")
