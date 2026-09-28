"""Search over the Mo Betta data: items, NPCs and mobs, quests, recipes, and 'where' questions.

Every function returns plain dicts so the same results can be rendered as Discord embeds
(bot.py) or as text (cli.py). Matching is: exact name, then prefix, then every query word
present in the name, then close spelling (difflib).
"""
from __future__ import annotations

import difflib
import re
from typing import Iterable

from data import CLASS_BY_NAME, CLASS_CODES, SLOTS, Store, norm


def rank(query: str, names: Iterable[str], limit: int = 8) -> list[str]:
    q = norm(query)
    if not q:
        return []
    names = list(names)
    exact = [n for n in names if norm(n) == q]
    prefix = [n for n in names if norm(n).startswith(q) and n not in exact]
    words = q.split()
    contains = [n for n in names if all(w in norm(n).split() or w in norm(n) for w in words)
                and n not in exact and n not in prefix]
    out = exact + sorted(prefix, key=len) + sorted(contains, key=len)
    if len(out) < limit:
        close = difflib.get_close_matches(q, [norm(n) for n in names], n=limit, cutoff=0.72)
        by_norm = {norm(n): n for n in names}
        out += [by_norm[c] for c in close if by_norm[c] not in out]
    return out[:limit]


# ---------------------------------------------------------------- items

def item(store: Store, query: str) -> dict | None:
    hit = rank(query, store.item_by_name.values() and (r["name"] for r in store.items), 1)
    return store.item_by_name.get(hit[0].lower()) if hit else None


def item_candidates(store: Store, query: str, limit: int = 25) -> list[str]:
    return rank(query, (r["name"] for r in store.items), limit)


def describe_item(store: Store, r: dict) -> dict:
    stats = r.get("stats", {})
    stat_line = "  ".join(f"{k.upper()} {v}" for k, v in stats.items())
    drops: list[str] = []
    seen: set[str] = set()
    for g in r.get("drops_from", []):
        for mob in g.get("mobs", []):
            if mob.lower() in seen:
                continue  # the wiki lists a mob once per zone it appears in
            seen.add(mob.lower())
            n = store.npc_by_name.get(mob.lower())
            loc = (n or {}).get("location") or (n or {}).get("zone") or g.get("zone", "")
            drops.append(f"{mob} ({loc})" if loc else mob)
    used_in = [x["name"] for x in store.recipes_using.get(r["name"].lower(), [])]
    made_by = [x for x in store.recipe_by_name.get(r["name"].lower(), [])]
    zones = {z.strip().lower() for n in store.npcs for z in n.get("zone", "").split(",")}
    sold_by = [s for s in r.get("sold_by", []) if s.lower() not in zones]  # item pages group vendors under zone headers
    for m in store.sellers_of.get(r["name"].lower(), []):  # merchant pages know more than item pages
        if m not in sold_by:
            n = store.npc_by_name.get(m.lower())
            loc = (n or {}).get("location") or (n or {}).get("zone") or ""
            sold_by.append(f"{m} ({loc})" if loc else m)
    return {
        "name": r["name"], "url": r["url"], "description": r.get("description", ""),
        "slot": r.get("slot", ""), "classes": expand_classes(r.get("classes", "")), "races": r.get("races", ""),
        "stats": stat_line, "effect": r.get("effect", ""), "flags": ", ".join(r.get("flags", [])),
        "weight": r.get("weight", ""), "drops": drops[:12], "sold_by": sold_by[:8],
        "quest_reward": r.get("quest_reward", [])[:6], "used_in": sorted(set(used_in))[:10],
        "made_by": [f"{m['skill']} (trivial {m['trivial']})" for m in made_by][:4], "id": r.get("id", ""),
        "image": r.get("image", ""),
    }


def expand_classes(codes: str) -> str:
    if not codes or codes.upper() == "ALL":
        return "All" if codes else ""
    return ", ".join(CLASS_CODES.get(c, c) for c in codes.split())


# ---------------------------------------------------------------- npcs / mobs

def npc(store: Store, query: str) -> dict | None:
    hit = rank(query, (r["name"] for r in store.npcs), 1)
    return store.npc_by_name.get(hit[0].lower()) if hit else None


def npc_candidates(store: Store, query: str, limit: int = 25) -> list[str]:
    return rank(query, (r["name"] for r in store.npcs), limit)


def describe_npc(store: Store, r: dict) -> dict:
    drops = sorted(store.drops_by_mob.get(r["name"].lower(), set()))
    quests = list(r.get("quests", []))
    # quests that mention this NPC anywhere (giver, related, dialogue)
    for q in store.quests:
        if r["name"].lower() in {n.lower() for n in q.get("npcs", [])} and q["title"] not in quests:
            quests.append(q["title"])
    return {
        "name": r["name"], "url": r["url"], "zone": r.get("zone", ""), "location": r.get("location", ""),
        "race": r.get("race", ""), "class": r.get("class", ""), "level": r.get("level", ""), "hp": r.get("hp", ""),
        "description": _clip(r.get("description", ""), 300), "drops": drops[:15], "factions": r.get("factions", [])[:5],
        "opposing": r.get("opposing_factions", [])[:5], "quests": quests[:8], "kind": r.get("kind", "npc"),
        "sells": r.get("sells", [])[:25], "buys": r.get("buys", [])[:10], "dialog": _clip(r.get("dialog", ""), 400),
        "image": r.get("image", ""),
    }


# ---------------------------------------------------------------- quests

def quest(store: Store, query: str) -> dict | None:
    hit = rank(query, (r["title"] for r in store.quests), 1)
    return store.quest_by_title.get(hit[0].lower()) if hit else None


def quest_candidates(store: Store, query: str, limit: int = 25) -> list[str]:
    return rank(query, (r["title"] for r in store.quests), limit)


def describe_quest(store: Store, q: dict) -> dict:
    steps = [s["text"] for s in q.get("steps", []) if s["text"].lower() not in ("bold text", "italic text")]
    says = [l["text"] for l in q.get("lines", []) if l["kind"] == "say"]
    items = sorted({it["name"] for s in q.get("steps", []) for it in s.get("items", [])})
    return {
        "title": q["title"], "url": q["url"], "zone": q.get("zone", ""), "giver": q.get("giver", ""),
        "level": q.get("min_level", ""), "classes": q.get("classes", ""), "npcs": q.get("npcs", []),
        "rewards": q.get("rewards", []), "steps": steps[:12], "say": says[:8], "items": items[:10],
    }


# ---------------------------------------------------------------- recipes

def recipe(store: Store, query: str) -> list[dict]:
    hit = rank(query, store.recipe_by_name.keys() and (n for n in {r["name"] for r in store.recipes}), 1)
    return store.recipe_by_name.get(hit[0].lower(), []) if hit else []


def recipe_candidates(store: Store, query: str, limit: int = 25) -> list[str]:
    return rank(query, {r["name"] for r in store.recipes}, limit)


def describe_recipe(r: dict) -> dict:
    ing = [f"{i['qty']} x {i['name']}" + (" (tool)" if i.get("tool") else "") if i.get("qty", 1) != 1
           else i["name"] + (" (tool)" if i.get("tool") else "") for i in r.get("ingredients", [])]
    return {"name": r["name"], "skill": r.get("skill", ""), "trivial": r.get("trivial", ""), "station": r.get("station", ""),
            "makes": r.get("makes", 1), "ingredients": ing, "notes": r.get("notes", ""), "url": r.get("url", "")}


# ---------------------------------------------------------------- where / drops / gear

def where(store: Store, query: str) -> dict:
    """An NPC's location, or where an item comes from, whichever the name matches better."""
    n_hit = rank(query, (r["name"] for r in store.npcs), 1)
    i_hit = rank(query, (r["name"] for r in store.items), 1)
    q = norm(query)
    if n_hit and (not i_hit or norm(n_hit[0]) == q or norm(i_hit[0]) != q):
        r = store.npc_by_name[n_hit[0].lower()]
        return {"kind": "npc", "name": r["name"], "zone": r.get("zone", ""), "location": r.get("location", ""), "url": r["url"]}
    if i_hit:
        d = describe_item(store, store.item_by_name[i_hit[0].lower()])
        return {"kind": "item", "name": d["name"], "drops": d["drops"], "sold_by": d["sold_by"],
                "quest_reward": d["quest_reward"], "made_by": d["made_by"], "url": d["url"]}
    return {"kind": "none", "name": query}


def drops(store: Store, mob_query: str) -> dict:
    hit = rank(mob_query, store.drops_by_mob.keys() and (n for n in store.npc_by_name.values() and (r["name"] for r in store.npcs)), 1)
    if not hit:
        return {"name": mob_query, "items": []}
    name = hit[0]
    return {"name": name, "items": sorted(store.drops_by_mob.get(name.lower(), set()))[:25]}


def gear(store: Store, klass: str, slot: str | None = None, stat: str | None = None, limit: int = 15) -> dict:
    code = CLASS_BY_NAME.get(klass.lower().strip())
    if not code:
        return {"error": f"unknown class '{klass}'; try one of {', '.join(CLASS_CODES.values())}"}
    slot_u = (slot or "").upper().strip()
    rows = []
    for r in store.items:
        cl = r.get("classes", "").upper()
        if cl != "ALL" and code not in cl.split():
            continue
        if slot_u and slot_u not in r.get("slot", "").upper().split():
            continue
        if not r.get("stats") and not r.get("effect"):
            continue
        rows.append(r)
    key = (stat or "").lower()
    if key:
        rows = [r for r in rows if key in r.get("stats", {})]
        rows.sort(key=lambda r: -_num(r["stats"].get(key, "0")))
    else:
        rows.sort(key=lambda r: -(_num(r.get("stats", {}).get("ac", "0")) + sum(_num(v) for k, v in r.get("stats", {}).items() if k in ("str", "sta", "agi", "dex", "int", "wis", "cha"))))
    out = []
    for r in rows[:limit]:
        st = "  ".join(f"{k.upper()} {v}" for k, v in r.get("stats", {}).items())
        out.append({"name": r["name"], "slot": r.get("slot", ""), "stats": st, "url": r["url"]})
    return {"class": CLASS_CODES[code], "slot": slot_u or "any", "stat": key or "", "items": out, "total": len(rows)}


# ---------------------------------------------------------------- zones

def zone(store: Store, query: str) -> dict | None:
    hit = rank(query, (z["name"] for z in store.zones), 1)
    return store.zone_by_name.get(hit[0].lower()) if hit else None


def zone_candidates(store: Store, query: str, limit: int = 25) -> list[str]:
    return rank(query, (z["name"] for z in store.zones), limit) if query else [z["name"] for z in store.zones][:limit]


def describe_zone(store: Store, z: dict) -> dict:
    here = store.npcs_in_zone.get(norm(z["name"]), [])
    generic = lambda n: n["name"].lower().startswith(("a ", "an "))  # "a black rat" is a mob, not a quest giver
    givers = [n for n in here if n.get("quests") and n.get("kind") != "merchant" and not generic(n)]
    merchants = [n for n in here if n.get("kind") == "merchant"]
    mobs = [n for n in here if n.get("kind") != "merchant" and not n.get("quests") and n.get("loot")]

    def with_loc(n: dict) -> str:
        return f"{n['name']} ({n['location']})" if n.get("location") else n["name"]

    return {
        "name": z["name"], "url": z["url"], "description": z.get("description", ""), "level": z.get("level", ""),
        "monsters": z.get("monsters", []), "adjacent": z.get("adjacent", []), "quests": z.get("quests", [])[:12],
        "givers": [f"{with_loc(n)}: {', '.join(n['quests'][:2])}" for n in givers[:12]],
        "merchants": [f"{with_loc(n)}: {', '.join(n.get('sells', [])[:4])}{'...' if len(n.get('sells', [])) > 4 else ''}" for n in merchants[:10]],
        "mobs": [f"{n['name']}" + (f" (lvl {n['level']})" if n.get("level") else "") for n in sorted(mobs, key=lambda n: _num(n.get("level", "0")))[:20]],
        "notable_npcs": z.get("notable_npcs", [])[:10], "notable_items": z.get("notable_items", [])[:12],
        "image": z.get("image", ""), "map": z.get("map", ""),
        "counts": {"npcs": len(here), "merchants": len(merchants), "quest givers": len(givers)},
    }


# ---------------------------------------------------------------- selling

def sell(store: Store, query: str, zone_name: str | None = None) -> dict:
    """Who buys this? Merchant pages list what they buy ('Hides', 'Bags and packs', 'about anything')."""
    q = norm(query)
    words = [w for w in q.split() if len(w) > 2]
    item = store.item_by_name.get(query.lower())
    kinds = set(words)
    if item:  # add hints from the item itself: slot words, and a few category words from its description
        kinds |= {w for w in norm(item.get("slot", "")).split()}
        kinds |= {w for w in norm(item.get("description", "")).split() if w in ("hide", "hides", "pelt", "bag", "gem", "ore", "cloth", "meat", "food", "weapon", "armor", "armour", "bone", "potion", "scroll", "jewelry", "jewellery")}
    matches: list[dict] = []
    anything: list[dict] = []
    for n in store.npcs:
        if n.get("kind") != "merchant":
            continue
        if zone_name and norm(zone_name) not in norm(n.get("zone", "")):
            continue
        buys = " ".join(n.get("buys", [])).lower()
        if not buys:
            continue
        if re.search(r"\b(anything|everything|all items|most items|any item)\b", buys):
            anything.append(n)
        elif any(k.rstrip("s") in buys for k in kinds):
            matches.append(n)

    def line(n: dict) -> str:
        where = " · ".join(x for x in (n.get("zone", ""), n.get("location", "")) if x)
        return f"{n['name']} ({where}) buys {', '.join(n.get('buys', [])[:3])}"

    return {"query": query, "zone": zone_name or "", "matches": [line(n) for n in matches[:10]],
            "anything": [line(n) for n in anything[:8]]}


def _clip(s: str, n: int) -> str:
    """Some wiki descriptions paste whole conversations; keep the first sentences."""
    if len(s) <= n:
        return s
    cut = s[:n]
    i = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[: i + 1] if i > 40 else cut.rsplit(" ", 1)[0] + "...")


def _num(v: str) -> float:
    try:
        return float(str(v).replace("%", "").strip() or 0)
    except ValueError:
        return 0.0
