from __future__ import annotations

import datetime
import random
from typing import TYPE_CHECKING
import zoneinfo

import discord
from discord.ext import commands, tasks

if TYPE_CHECKING:
    from marketmaker.subclass import GameVars

time = datetime.time(hour=0, minute=0, tzinfo=zoneinfo.ZoneInfo("Canada/Eastern"))

class BotTasks(commands.Cog):
    def __init__(self: BotTasks, bot) -> None:
        self.bot = bot
        self.daily_events.start()
        if self.bot.timed:
            self.timed_puzzle.start(self.bot.game_vars)

    @tasks.loop(time=time)
    async def daily_events(self: BotTasks) -> None:
        print("Daily reset!")

        channel: discord.TextChannel = await self.bot.fetch_channel(int(self.bot.channelid))

        eco = self.bot.get_cog("Economy")
        await eco.tax(channel)

        lb = self.bot.get_cog("Leaderboard")
        await lb.reset_timer_board(channel)


    @tasks.loop(seconds=random.randint(60, 600))
    async def timed_puzzle(self: BotTasks, game_vars: GameVars) -> None:
        if game_vars.seeking_substr == "":
            channel = await self.bot.fetch_channel(int(float(self.bot.channelid)))

            if not isinstance(channel, discord.TextChannel):
                raise Exception("Provided CHANNEL points to a non-text channel.")

            puzzle = self.bot.get_cog("Puzzle")
            await puzzle.spawn_puzzle(channel, self.bot.game_vars)

    @daily_events.before_loop
    async def before_daily_events(self: BotTasks) -> None:
        await self.bot.wait_until_ready()

    @timed_puzzle.before_loop
    async def before_timed_puzzle(self: BotTasks) -> None:
        await self.bot.wait_until_ready()
