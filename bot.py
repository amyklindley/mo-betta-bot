#!/usr/bin/env python3
"""Mo Betta Bot: slash commands for Monsters & Memories items, NPCs, quests and recipes.

Setup (once):
  1. https://discord.com/developers/applications -> New Application -> Bot -> Reset Token, copy it.
  2. Put the token in a file named .env next to this script:   DISCORD_TOKEN=xxxxx
  3. OAuth2 -> URL Generator: scopes `bot` + `applications.commands`; permissions Send Messages,
     Embed Links, Use Application Commands. Open the URL to invite the bot to your server.
  4. python bot.py
  5. In Discord, an admin runs /mobetta setup in the channel the bot should answer in.

Optional .env keys:  GUILD_ID=<server id>  (commands appear instantly in that server instead of
taking up to an hour to propagate globally)
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import discord
from discord import app_commands

import config
import render
import search
from data import CLASS_CODES, SLOTS, Store

HERE = Path(__file__).resolve().parent
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mobetta")


def load_env() -> None:
    p = HERE / ".env"
    if p.exists():
        for line in p.read_text("utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


store = Store()
intents = discord.Intents.none()
intents.guilds = True  # needed to know which servers the bot is in; no message content, no members
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


async def daily_refresh() -> None:
    while True:
        await asyncio.sleep(6 * 3600)
        updated = await asyncio.to_thread(store.refresh, False, log.info)
        if updated:
            log.info("data reloaded: %s", updated)


@client.event
async def on_ready() -> None:
    guild_id = os.environ.get("GUILD_ID")
    if guild_id:
        g = discord.Object(id=int(guild_id))
        tree.copy_global_to(guild=g)
        await tree.sync(guild=g)
    else:
        await tree.sync()
    client.loop.create_task(daily_refresh())
    log.info("ready as %s - %d items, %d npcs, %d quests, %d recipes", client.user, len(store.items), len(store.npcs),
             len(store.quests), len(store.recipes))


# ---------------------------------------------------------------- where and how to answer

async def reply(i: discord.Interaction, embed: discord.Embed | None = None, content: str | None = None) -> None:
    """Answer only in the configured channel (if one is set), as a message only the asker sees
    unless the server switched answers to public."""
    cfg = config.get(i.guild_id)
    if cfg["channel"] and i.channel_id != cfg["channel"]:
        await i.response.send_message(f"I answer in <#{cfg['channel']}>. Ask me there.", ephemeral=True)
        return
    await i.response.send_message(content=content, embed=embed, ephemeral=not cfg["public"])


# ---------------------------------------------------------------- autocomplete helpers

def choices(names: list[str]) -> list[app_commands.Choice[str]]:
    return [app_commands.Choice(name=n[:100], value=n[:100]) for n in names[:25]]


async def ac_item(_i: discord.Interaction, cur: str):
    return choices(search.item_candidates(store, cur)) if cur else []


async def ac_npc(_i: discord.Interaction, cur: str):
    return choices(search.npc_candidates(store, cur)) if cur else []


async def ac_quest(_i: discord.Interaction, cur: str):
    return choices(search.quest_candidates(store, cur)) if cur else []


async def ac_recipe(_i: discord.Interaction, cur: str):
    return choices(search.recipe_candidates(store, cur)) if cur else []


async def ac_class(_i: discord.Interaction, cur: str):
    return choices([c for c in CLASS_CODES.values() if cur.lower() in c.lower()])


async def ac_slot(_i: discord.Interaction, cur: str):
    return choices([s.title() for s in SLOTS if cur.upper() in s])


async def ac_zone(_i: discord.Interaction, cur: str):
    return choices(search.zone_candidates(store, cur))


# ---------------------------------------------------------------- commands

@tree.command(name="item", description="Look up an item: stats, who can use it, where it drops, recipes")
@app_commands.describe(name="Item name (autocompletes)")
@app_commands.autocomplete(name=ac_item)
async def cmd_item(i: discord.Interaction, name: str) -> None:
    r = search.item(store, name)
    if not r:
        return await reply(i, content=f"No item called **{name}**.")
    await reply(i, embed=render.item_embed(search.describe_item(store, r)))


@tree.command(name="npc", description="Look up an NPC, mob or merchant: where it is, what it drops or sells, its quests")
@app_commands.describe(name="NPC or mob name (autocompletes)")
@app_commands.autocomplete(name=ac_npc)
async def cmd_npc(i: discord.Interaction, name: str) -> None:
    r = search.npc(store, name)
    if not r:
        return await reply(i, content=f"No NPC called **{name}**.")
    await reply(i, embed=render.npc_embed(search.describe_npc(store, r)))


@tree.command(name="quest", description="Quest walkthrough: giver, steps, what to say, rewards")
@app_commands.describe(name="Quest name (autocompletes)")
@app_commands.autocomplete(name=ac_quest)
async def cmd_quest(i: discord.Interaction, name: str) -> None:
    q = search.quest(store, name)
    if not q:
        return await reply(i, content=f"No quest called **{name}**.")
    await reply(i, embed=render.quest_embed(search.describe_quest(store, q)))


@tree.command(name="where", description="Where is an NPC, or where does an item come from?")
@app_commands.describe(name="NPC or item name")
async def cmd_where(i: discord.Interaction, name: str) -> None:
    await reply(i, embed=render.where_embed(search.where(store, name)))


@tree.command(name="drops", description="What does a mob drop?")
@app_commands.describe(mob="Mob name (autocompletes)")
@app_commands.autocomplete(mob=ac_npc)
async def cmd_drops(i: discord.Interaction, mob: str) -> None:
    await reply(i, embed=render.drops_embed(search.drops(store, mob)))


@tree.command(name="gear", description="Best gear for a class, optionally one slot or one stat")
@app_commands.describe(class_name="Class", slot="Slot, e.g. Chest, Finger, Primary",
                       stat="Rank by one stat: ac, hp, mana, str, sta, agi, dex, int, wis, cha")
@app_commands.rename(class_name="class")
@app_commands.autocomplete(class_name=ac_class, slot=ac_slot)
async def cmd_gear(i: discord.Interaction, class_name: str, slot: str | None = None, stat: str | None = None) -> None:
    await reply(i, embed=render.gear_embed(search.gear(store, class_name, slot, stat)))


@tree.command(name="recipe", description="How is something crafted? Skill, trivial, station, ingredients")
@app_commands.describe(name="Recipe or item name (autocompletes)")
@app_commands.autocomplete(name=ac_recipe)
async def cmd_recipe(i: discord.Interaction, name: str) -> None:
    rs = search.recipe(store, name)
    if not rs:
        return await reply(i, content=f"No recipe for **{name}**.")
    await reply(i, embed=render.recipe_embed([search.describe_recipe(r) for r in rs]))


@tree.command(name="zone", description="A zone: levels, mobs, quest givers and merchants with locations, map")
@app_commands.describe(name="Zone name (autocompletes)")
@app_commands.autocomplete(name=ac_zone)
async def cmd_zone(i: discord.Interaction, name: str) -> None:
    z = search.zone(store, name)
    if not z:
        return await reply(i, content=f"No zone called **{name}**.")
    await reply(i, embed=render.zone_embed(search.describe_zone(store, z)))


@tree.command(name="sell", description="Who buys this, and where are they?")
@app_commands.describe(item="Item name or kind of thing, e.g. hides, gems, bags", zone="Only merchants in this zone")
@app_commands.autocomplete(item=ac_item, zone=ac_zone)
async def cmd_sell(i: discord.Interaction, item: str, zone: str | None = None) -> None:
    await reply(i, embed=render.sell_embed(search.sell(store, item, zone)))


# ---------------------------------------------------------------- /mobetta about | setup | anywhere

class MoBetta(app_commands.Group):
    """About the bot, and admin setup."""

    @app_commands.command(name="about", description="About this bot and how fresh its data is")
    async def about(self, i: discord.Interaction) -> None:
        f = store.fetched
        cfg = config.get(i.guild_id)
        where = f"<#{cfg['channel']}>" if cfg["channel"] else "any channel"
        visibility = "visible to everyone" if cfg["public"] else "visible only to whoever asked"
        msg = (
            "**Mo Betta Bot** - data from the Monsters and Memories community wiki\n"
            f"items {len(store.items)} (fetched {f.get('items.json', '?')}), npcs {len(store.npcs)} ({f.get('npcs.json', '?')}), "
            f"quests {len(store.quests)} ({f.get('quests.json', '?')}), recipes {len(store.recipes)} ({f.get('recipes.json', '?')})\n"
            f"Answers in {where}, {visibility}.\n"
            "Commands: /item /npc /quest /zone /where /drops /sell /gear /recipe\n"
            "Source: https://github.com/amyklindley/mo-betta-bot"
        )
        await i.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="setup", description="Admins: pick the one channel the bot answers in, and whether answers are public")
    @app_commands.describe(channel="Channel to answer in (default: this one)",
                           public="Answers visible to everyone instead of only the asker")
    @app_commands.default_permissions(manage_guild=True)
    async def setup(self, i: discord.Interaction, channel: discord.TextChannel | None = None,
                    public: bool | None = None) -> None:
        if i.guild_id is None:
            await i.response.send_message("Run this in a server.", ephemeral=True)
            return
        target_id = channel.id if channel else i.channel_id
        config.set_channel(i.guild_id, target_id)
        if public is not None:
            config.set_public(i.guild_id, public)
        cfg = config.get(i.guild_id)
        visibility = "visible to everyone" if cfg["public"] else "as messages only the asker can see"
        await i.response.send_message(
            f"Done. I answer only in <#{target_id}>, {visibility}. Use `/mobetta anywhere` to lift the channel limit.",
            ephemeral=True)

    @app_commands.command(name="anywhere", description="Admins: let the bot answer in any channel again")
    @app_commands.default_permissions(manage_guild=True)
    async def anywhere(self, i: discord.Interaction) -> None:
        if i.guild_id is None:
            await i.response.send_message("Run this in a server.", ephemeral=True)
            return
        config.set_channel(i.guild_id, None)
        await i.response.send_message("Done. I answer in any channel now.", ephemeral=True)


tree.add_command(MoBetta(name="mobetta", description="About the bot, and admin setup"))


def main() -> None:
    load_env()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN missing: put it in .env next to bot.py (see the docstring at the top).")
    store.refresh(log=log.info)
    if not store.items:
        raise SystemExit("No data: the download from GitHub failed. Check your connection and try again.")
    client.run(token, log_handler=None)


if __name__ == "__main__":
    main()
