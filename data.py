"""Load the Mo Betta data files (quests, items, NPCs, recipes) and keep them fresh.

The JSON is scraped from the community wiki by the Mo Betta Quests / Crafts projects and
published in their GitHub repos. The bot downloads them into ./data on first run and checks
for newer copies once a day, so it never touches the wiki itself.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SOURCES = {
    "quests.json": "https://raw.githubusercontent.com/amyklindley/mo-betta-quests/main/quests.json",
    "items.json": "https://raw.githubusercontent.com/amyklindley/mo-betta-quests/main/items.json",
    "npcs.json": "https://raw.githubusercontent.com/amyklindley/mo-betta-quests/main/npcs.json",
    "zones.json": "https://raw.githubusercontent.com/amyklindley/mo-betta-quests/main/zones.json",
    "recipes.json": "https://raw.githubusercontent.com/amyklindley/mo-betta-crafts/main/recipes.json",
}
CHECK_EVERY = 24 * 3600
STAMP = DATA / "updates.json"

CLASS_CODES = {
    "ARC": "Archer", "BRD": "Bard", "BST": "Beastmaster", "CLR": "Cleric", "DRU": "Druid", "ELE": "Elementalist",
    "ENC": "Enchanter", "FTR": "Fighter", "INQ": "Inquisitor", "MNK": "Monk", "NEC": "Necromancer", "PAL": "Paladin",
    "RNG": "Ranger", "ROG": "Rogue", "SHD": "Shadow Knight", "SHM": "Shaman", "SPB": "Spellblade", "WIZ": "Wizard",
}
CLASS_BY_NAME = {v.lower(): k for k, v in CLASS_CODES.items()} | {k.lower(): k for k in CLASS_CODES}
CLASS_BY_NAME.update({"sk": "SHD", "shadowknight": "SHD", "shadow knight": "SHD", "pally": "PAL", "necro": "NEC",
                      "ench": "ENC", "ele": "ELE", "beast": "BST", "bm": "BST", "inq": "INQ", "spellblade": "SPB", "sb": "SPB"})
SLOTS = ["PRIMARY", "SECONDARY", "RANGE", "AMMO", "HEAD", "FACE", "EAR", "NECK", "SHOULDERS", "ARMS", "WRIST", "HANDS",
         "FINGER", "CHEST", "BACK", "WAIST", "BELT", "LEGS", "FEET", "CHARM"]


class Store:
    def __init__(self) -> None:
        self.loaded_at = 0.0
        self.quests: list[dict] = []
        self.items: list[dict] = []
        self.npcs: list[dict] = []
        self.zones: list[dict] = []
        self.recipes: list[dict] = []
        self.fetched: dict[str, str] = {}

    # ---------------------------------------------------------------- files

    def refresh(self, force: bool = False, log=print) -> list[str]:
        """Download any source that changed (ETag) and reload. Returns updated file names."""
        DATA.mkdir(exist_ok=True)
        try:
            stamps = json.loads(STAMP.read_text("utf-8"))
        except (OSError, ValueError):
            stamps = {}
        updated: list[str] = []
        now = time.time()
        for name, url in SOURCES.items():
            st = stamps.get(name, {})
            path = DATA / name
            if not force and path.exists() and now - st.get("checked", 0) < CHECK_EVERY:
                continue
            req = urllib.request.Request(url, headers={"User-Agent": "MoBettaBot (data refresh)"})
            if st.get("etag") and path.exists():
                req.add_header("If-None-Match", st["etag"])
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    body, etag = r.read(), r.headers.get("ETag", "")
                json.loads(body)
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(body)
                tmp.replace(path)
                stamps[name] = {"etag": etag, "checked": now}
                updated.append(name)
                log(f"data: {name} updated ({len(body) // 1024} KB)")
            except urllib.error.HTTPError as e:
                if e.code == 304:
                    stamps[name] = {"etag": st.get("etag", ""), "checked": now}
                else:
                    log(f"data: {name} not updated (HTTP {e.code})")
            except Exception as e:  # noqa: BLE001
                log(f"data: {name} not updated ({e.__class__.__name__})")
        try:
            STAMP.write_text(json.dumps(stamps), "utf-8")
        except OSError:
            pass
        if updated or not self.loaded_at:
            self.load()
        return updated

    def load(self) -> None:
        def read(name: str, key: str) -> list[dict]:
            try:
                d = json.loads((DATA / name).read_text("utf-8"))
                self.fetched[name] = d.get("fetched", "")
                return d.get(key, [])
            except (OSError, ValueError):
                return []
        self.quests = read("quests.json", "quests")
        self.items = read("items.json", "items")
        self.npcs = read("npcs.json", "npcs")
        self.zones = read("zones.json", "zones")
        self.recipes = read("recipes.json", "recipes") or _flatten_recipes(name="recipes.json")
        self.loaded_at = time.time()
        self._index()

    # ---------------------------------------------------------------- indexes

    def _index(self) -> None:
        self.item_by_name = {r["name"].lower(): r for r in self.items}
        self.npc_by_name = {r["name"].lower(): r for r in self.npcs}
        self.quest_by_title = {r["title"].lower(): r for r in self.quests}
        self.recipe_by_name: dict[str, list[dict]] = {}
        for r in self.recipes:
            self.recipe_by_name.setdefault(r["name"].lower(), []).append(r)
        # who drops what (from item pages) and who is in which zone
        self.drops_by_mob: dict[str, set[str]] = {}
        for it in self.items:
            for g in it.get("drops_from", []):
                for mob in g.get("mobs", []):
                    self.drops_by_mob.setdefault(mob.lower(), set()).add(it["name"])
        for n in self.npcs:
            for loot in n.get("loot", []):
                self.drops_by_mob.setdefault(n["name"].lower(), set()).add(loot)
        # who sells what (from merchant pages), and who lives where
        self.sellers_of: dict[str, list[str]] = {}
        self.npcs_in_zone: dict[str, list[dict]] = {}
        for n in self.npcs:
            for it in n.get("sells", []):
                self.sellers_of.setdefault(it.lower(), []).append(n["name"])
            for z in n.get("zone", "").split(","):
                if z.strip():
                    self.npcs_in_zone.setdefault(norm(z), []).append(n)
        self.zone_by_name = {z["name"].lower(): z for z in self.zones}
        # recipes that use an item
        self.recipes_using: dict[str, list[dict]] = {}
        for r in self.recipes:
            for ing in r.get("ingredients", []):
                self.recipes_using.setdefault(ing["name"].lower(), []).append(r)


def _flatten_recipes(name: str) -> list[dict]:
    """recipes.json from Mo Betta Crafts may be a dict keyed by skill; flatten to a list."""
    try:
        d = json.loads((DATA / name).read_text("utf-8"))
    except (OSError, ValueError):
        return []
    rows = d.get("recipes", d)
    if isinstance(rows, dict):
        out = []
        for v in rows.values():
            out += v if isinstance(v, list) else [v]
        return out
    return rows if isinstance(rows, list) else []


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
