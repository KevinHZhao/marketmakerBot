from __future__ import annotations

import asyncio
import logging
import sys

import discord

import marketmaker.actions
import marketmaker.cmnds
from marketmaker.initialization import ensure_db, ensure_substr
from marketmaker.subclass import MarketmakerBot

root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

intents = discord.Intents.default()
intents.message_content = True

prefix = "##"
bot = MarketmakerBot(command_prefix=prefix, intents=intents)

# Game data init
ensure_substr(bot.normal_min_words, bot.hard_min_words)
ensure_db()

@bot.event
async def on_ready() -> None:
    print(f"We have logged in as {bot.user}")
    print(bot.guilds)

    await bot.tree.sync()


# Make the bot runnable from CLI (main must be a function)
async def main() -> None:
    for c in marketmaker.cmnds.cogs:
        await bot.add_cog(c(bot))

    for c in marketmaker.actions.cogs:
        await bot.add_cog(c(bot))

    await bot.start(bot.BOT_TOKEN)

asyncio.run(main())

# if __name__ == "__main__":
#     # this allows you to run the bot from this script too
#     # Doesn't seem to work with async run_bot...
#     run_bot()
