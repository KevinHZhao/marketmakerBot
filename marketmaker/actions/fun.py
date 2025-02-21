from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    import discord


class Fun(commands.Cog):
    def __init__(self: Fun, bot) -> None:
        self.bot = bot


    async def fish_react(self: Fun, message: discord.Message) -> None:
        """
        Adds a fish reaction to a message,
        and sends a message to the channel
        encouraging further reactions.

        Parameters
        ----------
        message : Message
            The message to react to.

        """
        FISH = ["🐟", "🐠", "🐡", "🎣", "🦈"]
        GIF_LINK = "https://tenor.com/view/fish-react-fish-react-him-thanos-gif-26859685"
        for fish in FISH:
            await message.add_reaction(fish)

        await message.channel.send(GIF_LINK)