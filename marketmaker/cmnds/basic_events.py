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

        await self.bot.process_commands(message)

        if message.content.startswith(self.bot.command_prefix):
            return

        if (
            random.randrange(100) < self.bot.prob_coin
            and self.bot.game_vars.seeking_substr == ""
            and message.guild
        ):
            puzzle = self.bot.get_cog("Puzzle")
            await puzzle.spawn_puzzle(message.channel, self.bot.game_vars)
