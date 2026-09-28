#!/usr/bin/env python3
"""Try the bot's searches without Discord.

  python cli.py item "fire beetle eye"
  python cli.py npc "old rankle"
  python cli.py quest "bone chips"
  python cli.py where "old rankle"      python cli.py where "ashira tail"
  python cli.py drops "a grain beetle"
  python cli.py gear paladin [slot] [stat]
  python cli.py recipe "bolt of cloth"
"""
from __future__ import annotations

import sys

import render
import search
from data import Store


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        raise SystemExit(__doc__)
    kind, q = argv[0], argv[1]
    store = Store()
    store.refresh(log=lambda m: None)
    if kind == "item":
        r = search.item(store, q)
        print(render.text(search.describe_item(store, r), "item") if r else "not found")
    elif kind == "npc":
        r = search.npc(store, q)
        print(render.text(search.describe_npc(store, r), "npc") if r else "not found")
    elif kind == "quest":
        r = search.quest(store, q)
        print(render.text(search.describe_quest(store, r), "quest") if r else "not found")
    elif kind == "where":
        print(render.text(search.where(store, q), "where"))
    elif kind == "drops":
        print(render.text(search.drops(store, q), "drops"))
    elif kind == "gear":
        print(render.text(search.gear(store, q, argv[2] if len(argv) > 2 else None, argv[3] if len(argv) > 3 else None), "gear"))
    elif kind == "zone":
        z = search.zone(store, q)
        print(render.text(search.describe_zone(store, z), "zone") if z else "not found")
    elif kind == "sell":
        print(render.text(search.sell(store, q, argv[2] if len(argv) > 2 else None), "sell"))
    elif kind == "recipe":
        rs = search.recipe(store, q)
        print(render.text([search.describe_recipe(r) for r in rs], "recipe") if rs else "not found")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
