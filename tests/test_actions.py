from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from discord import TextChannel

    from marketmaker.subclass import MarketmakerBot


@pytest.mark.bot
async def test_fish_react(bot: MarketmakerBot, channel: TextChannel, event_loop):
    # send a base message

    loop = asyncio.get_running_loop()

    message = await channel.send("Test message")

    # call the function
    funf = bot.get_cog("Fun")
    await funf.fish_react(message)

    # check if the message has the fish reaction; re-fetch
    FISH = ["🐟", "🐠", "🐡", "🎣", "🦈"]
    message = await channel.fetch_message(message.id)
    for fish in FISH:
        assert any(reaction.emoji == fish for reaction in message.reactions)

    # check if the bot sent a message
    history = [msg async for msg in channel.history(limit=1)]
    assert (
        "https://tenor.com/view/fish-react-fish-react-him-thanos-gif-26859685"
        in history[0].content
    )
