from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from marketmaker.backend.db import (
    leaderboard_backend,
    reset_timer_board_backend,
    build_board,
    StatType,
)

if TYPE_CHECKING:
    import discord


class Leaderboard(commands.Cog):
    def __init__(self: Leaderboard, bot) -> None:
        self.bot = bot


    async def reset_timer_board(self: Leaderboard, channel: discord.TextChannel) -> None:
        reset_timer_board_backend()
        await channel.send("The time trial leaderboard has been reset!")


    async def build_leaderboard(self: Leaderboard) -> None | str:
        rows = leaderboard_backend()
        if rows is None:
            return None

        board = ""
        for row, i in zip(rows, range(len(rows)), strict=False):
            board += f"{i + 1}. {await self.bot.fetch_user(row[0])}: {row[1]}$\n"

        return board


    async def ledger_board(self: Leaderboard, stat: StatType) -> None | str:
        table = build_board(stat)
        if table is None:
            return None

        return "\n".join([f"{i+1}. {await self.bot.fetch_user(row['sender'])}: {row['amount']}$" for i, row in table.iterrows()])
