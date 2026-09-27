# Mo Betta Bot

A Discord bot that answers Monsters & Memories questions from the same wiki data the
Mo Betta Quests and Mo Betta Crafts overlays use: about 4,900 items, 1,800 NPCs and
mobs, 117 quest walkthroughs and 1,400 recipes. Slash commands with autocomplete.

| Command | What you get |
|---|---|
| `/item <name>` | description, slot, classes, races, stats, effect, drops from (with the mob's location), sold by, quest reward, crafted by, used in recipes |
| `/npc <name>` | zone and location, race/class/level, what it drops, its quests, faction |
| `/quest <name>` | giver, zone, level, class, steps, what to say, items needed, rewards |
| `/where <name>` | an NPC's location, or an item's drop sources / vendors / recipe |
| `/drops <mob>` | everything a mob drops |
| `/gear <class> [slot] [stat]` | best items a class can wear, optionally one slot, ranked by one stat |
| `/recipe <name>` | skill, trivial, station, ingredients |
| `/mobetta about` | data freshness, where it answers, links |
| `/mobetta setup [channel] [public]` | admins only: lock the bot to one channel (default: the one you run it in); `public: True` makes answers visible to everyone |
| `/mobetta anywhere` | admins only: lift the channel limit |

Answers are private by default: only the person who asked sees them, with Discord's
"Dismiss message" link, so the bot never clutters a channel. Asking from the wrong
channel gets a private pointer to the right one.

## Run it

1. Python 3.11+ and `python -m pip install -r requirements.txt`.
2. Create the bot at <https://discord.com/developers/applications>: **New Application**,
   then **Bot**, then **Reset Token** and copy it. No privileged intents are needed.
3. Save the token in a file named `.env` next to `bot.py`:
   ```
   DISCORD_TOKEN=paste-it-here
   GUILD_ID=your-server-id      (optional: commands show up instantly in that server)
   ```
4. **OAuth2 → URL Generator**: scopes `bot` and `applications.commands`; permissions
   *Send Messages*, *Embed Links*, *Use Application Commands*. Open the generated URL and
   add the bot to your server.
5. `python bot.py` (or `run.bat`). The first start downloads the four data files into
   `data/`; after that it checks GitHub for newer copies every six hours. The bot never
   touches the wiki itself.

The bot only runs while that script runs. For an always-on bot, run it on any small
always-on machine: a spare PC, a Raspberry Pi, or a $5/month VPS. It needs no database
and about 150 MB of RAM.

## Try searches without Discord

```
python cli.py item "fire beetle eye"
python cli.py where "old rankle"
python cli.py gear paladin chest ac
```

## Data

`quests.json`, `items.json`, `npcs.json` come from
[mo-betta-quests](https://github.com/amyklindley/mo-betta-quests) and `recipes.json` from
[mo-betta-crafts](https://github.com/amyklindley/mo-betta-crafts), all scraped from the
[Monsters and Memories community wiki](https://monstersandmemories.miraheze.org). The wiki
is volunteer-written; gaps in the answers are gaps on the wiki, and fixing the wiki fixes
the bot within a day.

## License

MIT. Recipe, item, NPC and quest data belong to the wiki's contributors under that wiki's
content license.
