from __future__ import annotations

from datetime import datetime, time
from pytz import timezone
import random
import sqlite3
from typing import TYPE_CHECKING
import zoneinfo

import discord
from discord.ext import commands, tasks

from marketmaker.backend.futures import (
    resolve_futures
)

if TYPE_CHECKING:
    from marketmaker.subclass import GameVars

time = time(hour=0, minute=0, tzinfo=zoneinfo.ZoneInfo("Canada/Eastern"))

class BotTasks(commands.Cog):
    def __init__(self: BotTasks, bot) -> None:
        self.bot = bot
        self.daily_events.start()
        self.expire_futures.start()
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

    @tasks.loop(minutes=1.0)
    async def expire_futures(self: BotTasks) -> None:
        current_time = (datetime.now(timezone("US/Eastern")))
        conn = sqlite3.connect("marketmaker.db")
        cur = conn.cursor()

        # Fetch events that are due
        cur.execute("""
        SELECT ID, CID, init_economy, premium, target_growth, return_rate
        FROM futures
        WHERE end <= ?
        """, (current_time,))

        events = cur.fetchall()

        for event in events:
            user_id, channel_id, init_economy, premium, target_growth, return_rate = event
            payout = resolve_futures(user_id, init_economy, target_growth, return_rate)

            # Send the event message to the channel
            channel = await self.bot.fetch_channel(int(channel_id))
            user = await self.bot.fetch_user(int(user_id))
            if channel:
                await channel.send(f"{user.mention}, your {premium}$ {"put for the economy to deflate" if target_growth < 0 else "call for the economy to inflate"} by {abs(target_growth)} has expired! You have received {payout}$, resulting in a net {"gain" if payout >= premium else "loss"} of {abs(payout - premium)}$!")

            # Remove these events from the database
            cur.execute("DELETE FROM futures WHERE ID = ?", (user_id,))

        conn.commit()
        conn.close()