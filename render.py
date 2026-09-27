"""Turn search results into Discord embeds, or plain text for the CLI."""
from __future__ import annotations

try:
    import discord
except ImportError:  # CLI-only use
    discord = None

GOLD = 0xD9A441


def _embed(title: str, url: str = "", description: str = "") -> "discord.Embed":
    e = discord.Embed(title=title, url=url or None, description=description[:4000] or None, colour=GOLD)
    return e


def _field(e, name: str, value, inline: bool = False) -> None:
    if isinstance(value, (list, tuple)):
        value = "\n".join(f"• {v}" for v in value)
    if value:
        e.add_field(name=name, value=str(value)[:1024], inline=inline)


# ---------------------------------------------------------------- embeds

def item_embed(d: dict):
    e = _embed(d["name"], d["url"], d["description"])
    _field(e, "Slot", d["slot"], True)
    _field(e, "Classes", d["classes"], True)
    _field(e, "Races", d["races"] if d["races"].upper() != "ALL" else "", True)
    _field(e, "Stats", d["stats"])
    _field(e, "Effect", d["effect"])
    _field(e, "Flags", d["flags"], True)
    _field(e, "Weight", d["weight"], True)
    _field(e, "Drops from", d["drops"])
    _field(e, "Sold by", d["sold_by"])
    _field(e, "Quest reward", d["quest_reward"])
    _field(e, "Crafted by", d["made_by"])
    _field(e, "Used in recipes", d["used_in"])
    e.set_footer(text="Source: Monsters and Memories community wiki")
    return e


def npc_embed(d: dict):
    e = _embed(d["name"], d["url"], d["description"])
    where = " · ".join(x for x in (d["zone"], d["location"]) if x)
    _field(e, "Where", where)
    _field(e, "Race / class", " ".join(x for x in (d["race"], d["class"]) if x), True)
    _field(e, "Level", d["level"], True)
    _field(e, "HP", d["hp"], True)
    _field(e, "Drops", d["drops"])
    _field(e, "Quests", d["quests"])
    _field(e, "Faction", d["factions"], True)
    _field(e, "Opposes", d["opposing"], True)
    e.set_footer(text="Source: Monsters and Memories community wiki")
    return e


def quest_embed(d: dict):
    meta = " · ".join(x for x in (f"lvl {d['level']}" if d["level"] else "", d["zone"], d["classes"]) if x)
    e = _embed(d["title"], d["url"], meta)
    _field(e, "Quest giver", d["giver"], True)
    _field(e, "NPCs", ", ".join(d["npcs"]))
    _field(e, "Steps", d["steps"])
    _field(e, "Say", [f'"{s}"' for s in d["say"]])
    _field(e, "Items", d["items"])
    _field(e, "Rewards", d["rewards"])
    e.set_footer(text="Source: Monsters and Memories community wiki")
    return e


def recipe_embed(rs: list[dict]):
    first = rs[0]
    e = _embed(first["name"], first["url"])
    for d in rs[:4]:
        head = " · ".join(x for x in (d["skill"], f"trivial {d['trivial']}" if d["trivial"] not in ("", None) else "",
                                       d["station"], f"makes {d['makes']}" if d["makes"] and d["makes"] != 1 else "") if x)
        body = "\n".join(f"• {i}" for i in d["ingredients"]) + (f"\n_{d['notes']}_" if d["notes"] else "")
        e.add_field(name=head or d["skill"], value=body[:1024] or "-", inline=False)
    e.set_footer(text="Source: Monsters and Memories community wiki")
    return e


def where_embed(d: dict):
    if d["kind"] == "npc":
        e = _embed(d["name"], d["url"], " · ".join(x for x in (d["zone"], d["location"]) if x) or "location unknown")
    elif d["kind"] == "item":
        e = _embed(d["name"], d["url"])
        _field(e, "Drops from", d["drops"] or "no drop sources listed")
        _field(e, "Sold by", d["sold_by"])
        _field(e, "Quest reward", d["quest_reward"])
        _field(e, "Crafted", d["made_by"])
    else:
        e = _embed(f"Nothing called '{d['name']}'", description="Try /item, /npc or /quest with autocomplete.")
    return e


def drops_embed(d: dict):
    e = _embed(f"{d['name']} drops", description="\n".join(f"• {i}" for i in d["items"]) or "nothing recorded")
    return e


def gear_embed(d: dict):
    if "error" in d:
        return _embed("Gear", description=d["error"])
    title = f"{d['class']} gear" + (f" · {d['slot']}" if d["slot"] != "any" else "") + (f" · best {d['stat'].upper()}" if d["stat"] else "")
    lines = [f"**[{i['name']}]({i['url']})** {i['slot'].lower()}\n{i['stats']}" for i in d["items"]]
    e = _embed(title, description="\n".join(lines)[:4000] or "nothing found")
    e.set_footer(text=f"{d['total']} matching items · showing top {len(d['items'])}")
    return e


# ---------------------------------------------------------------- plain text (CLI)

def text(d: dict | list, kind: str) -> str:
    if kind == "item":
        return "\n".join(f"{k}: {v}" for k, v in d.items() if v)
    if kind == "recipe":
        return "\n\n".join("\n".join(f"{k}: {v}" for k, v in r.items() if v) for r in d)
    return "\n".join(f"{k}: {v}" for k, v in d.items() if v)
