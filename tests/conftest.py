import asyncio
import os
from contextlib import suppress

import pytest
from discord import Guild, Intents
from discord.client import _LoopSentinel
from dotenv import load_dotenv

import marketmaker.actions
import marketmaker.cmnds
from marketmaker.initialization import ensure_db, ensure_substr
from marketmaker.subclass import MarketmakerBot


# Test config options
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-bot",
        action="store_true",
        help="Run bot integration tests",
    )


# Apply flags
def pytest_collection_modifyitems(config, items):
    # Skip certain tests if the user doesn't specify the option
    if not config.getoption("--run-bot"):
        skip_bot = pytest.mark.skip(reason="need --run-bot option to run")
        for item in items:
            if "bot" in item.keywords:
                item.add_marker(skip_bot)


pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(scope="session")
def event_loop(bot: MarketmakerBot):
    # use the bot's event loop for asyncio stuff,
    # because we cannot assign our own loop to discord.py
    return bot.loop


# reusable bot fixture
@pytest.fixture(scope="session")
async def bot():
    load_dotenv(override=True)

    intents = Intents.default()
    intents.message_content = True
    bot = MarketmakerBot(command_prefix="##", intents=intents)

    ensure_substr(bot.normal_min_words, bot.hard_min_words)
    ensure_db()

    for c in marketmaker.cmnds.cogs:
        await bot.add_cog(c(bot))

    for c in marketmaker.actions.cogs:
        await bot.add_cog(c(bot))

    # Log in & start bot without blocking
    await bot.login(os.getenv("BOT_TOKEN"))
    bot_task = asyncio.create_task(bot.connect())
    await bot.wait_until_ready()
    yield bot

    # Teardown
    bot_task.cancel()
    try:
        await bot.close()
        await bot_task
    except asyncio.CancelledError:
        pass


@pytest.fixture(scope="session")
async def guild(bot: MarketmakerBot):
    guild = await bot.fetch_guild(int(os.getenv("TEST_GUILD_ID")))
    return guild


@pytest.fixture(scope="session")
async def channel(guild: Guild):
    channel = await guild.create_text_channel("auto-testing")
    yield channel
    # Teardown
    await channel.delete()
