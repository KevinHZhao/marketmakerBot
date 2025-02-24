from __future__ import annotations

import random

from discord.ext import commands


class BasicEvents(commands.Cog):
    def __init__(self: BasicEvents, bot) -> None:
        self.bot = bot


    @commands.Cog.listener()
    async def on_message(self: BasicEvents, message) -> None:
        if message.author.bot:
            return

        if message.content.startswith(self.bot.command_prefix):
            return

        puzzle = self.bot.get_cog("Puzzle")
        if (
            random.randrange(100) < self.bot.prob_coin
            and not puzzle.is_puzzle_running()
            and message.guild
        ):
            await puzzle.spawn_puzzle(message.channel, self.bot.game_vars)
