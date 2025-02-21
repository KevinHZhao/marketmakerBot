from __future__ import annotations

import asyncio
import datetime
import random
from typing import TYPE_CHECKING, Optional

from discord.ext import commands

from marketmaker.lib.bomb_party import check_bomb, finish_bomb, setup_bomb
from marketmaker.lib.db import (
    add_used_word,
    fetch_used_words,
    fetch_wallet_amount,
    timer_board_add,
)

if TYPE_CHECKING:
    import discord

    from marketmaker.subclass import GameVars


class Puzzle(commands.Cog):
    def __init__(self: Puzzle, bot) -> None:
        self.bot = bot


    async def spawn_puzzle(
        self: Puzzle,
        channel: discord.TextChannel,
        game_vars: GameVars,
        coin_value: Optional[int] = None,
        bonus_value: int = 100,
        anarchy_override: bool = False,
        anarchy_victim: discord.Member = None,
    ) -> None:
        bank_money = fetch_wallet_amount("BANK")
        total_money = fetch_wallet_amount("TOTAL")

        if game_vars.anarchy:
            game_vars.anarchy = bank_money < total_money / 5
        else:
            game_vars.anarchy = bank_money < total_money / 90

        if anarchy_override and fetch_wallet_amount(anarchy_victim.id) == 0:
            await channel.send(
                f"We were going to put all of {anarchy_victim.mention}'s money up for a puzzle, but they don't have any left!  Nothing happens..."
            )
            return

        bonus = game_vars.daily_counter > 0 and random.randrange(10) == 9
        coin_value, outcome = setup_bomb(game_vars, bonus, self.bot.normal_min_words, self.bot.hard_min_words, coin_value, anarchy_override, anarchy_victim)

        if game_vars.victimid is None:
            # This is a failsafe, but it should never be reached
            victim = "ERROR NO VICTIM"
            vicmen = "ERROR NO VICTIM"
        else:
            victim = await self.bot.fetch_user(game_vars.victimid)
            vicmen = victim.mention

        spawn_msgs = {
            1: f"{vicmen}, all {coin_value}$ from your wallet has spawned, unlucky!  Anyone can claim them by typing a word with `{game_vars.seeking_substr}` within 30 seconds!",
            2: f"The bank's looking pretty empty, so instead, :coin: Coins :coin: from {victim}'s wallet have spawned, valued at {coin_value}$!  You can claim them by typing a word with `{game_vars.seeking_substr}` within 30 seconds!",
            3: f":dollar: Bonus Coins :dollar: have spawned, valued at {coin_value + bonus_value}$!  You can claim them by typing a word with `{game_vars.seeking_substr}` within 30 seconds!",
            4: f":coin: Coins :coin: from the bank have spawned, valued at {coin_value}$!  You can claim them by typing a word with `{game_vars.seeking_substr}` within 30 seconds!",
        }

        announce = await channel.send(spawn_msgs[outcome], delete_after=30)

        results = await self.test_puzzle(channel, game_vars)

        if results is None:
            await self.failed_answer(game_vars, channel, coin_value)
        else:
            answer, elapsed_time = results

            if round(elapsed_time % 10, 2) == 7.27:
                extra_bonus = round(bonus_value * 7.27)
                bonus_value = bonus_value * bonus + extra_bonus
                bonus = True
                await channel.send(f"WYSI buff applied, extra bonus applied to this puzzle of {extra_bonus}$.")
            await self.complete_puzzle(
                announce,
                channel,
                game_vars,
                coin_value,
                bonus_value,
                answer,
                elapsed_time,
                bonus,
                anarchy_override,
                victim,
            )

        return 

    async def test_puzzle(
        self,
        channel: discord.TextChannel,
        game_vars: GameVars,
    ) -> tuple[discord.Message, float] | None:
        def check(m: discord.Message) -> bool:
            if not m.content:
                return False
            return (
                not m.author.bot
                and check_bomb(m.content, game_vars)
                and m.channel == channel
            )

        used_words = fetch_used_words()

        start_time = datetime.datetime.now()
        TIME_LIMIT_SEC = 30
        elapsed_time = 0.0
        try:
            # Keep listening for messages until 30 seconds have passed or a 👍 reaction is given
            while elapsed_time < TIME_LIMIT_SEC:
                try:
                    # Wait for a message (1 second timeout for each check)
                    msg = await self.bot.wait_for("message", check=check, timeout=1.0)

                    elapsed_time = (datetime.datetime.now() - start_time).total_seconds()

                    # If the message is in used_words, react with ❌ and continue checking
                    if msg.content.lower() in used_words:
                        await msg.add_reaction("❌")
                    else:
                        break  # End the game when a valid message is found

                except asyncio.TimeoutError:
                    elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
                    continue  # If no new message, continue the loop

            if elapsed_time >= TIME_LIMIT_SEC:
                raise asyncio.TimeoutError()
        except asyncio.TimeoutError:
            return None

        return (msg, elapsed_time)


    async def failed_answer(
        self: Puzzle,
        game_vars: GameVars,
        channel: discord.TextChannel,
        coin_value: int,
    ) -> None:
        victim = await self.bot.fetch_user(game_vars.victimid)
        if game_vars.anarchy:
            await channel.send(
                f"Time's up!  No one claimed the :coin: Coins :coin: so {victim}'s {coin_value}$ are going to the bank!",
                delete_after=10,
            )
            assert game_vars.victimid is not None
            assert isinstance(coin_value, int)
            eco = self.bot.get_cog("Economy")
            victim = await self.bot.fetch_user(game_vars.victimid)
            await eco.wallet_transfer(victim, "BANK", coin_value, channel, 3)
        else:
            await channel.send(
                "Time's up!  No one claimed the :coin: Coins :coin: so they've been returned to the bank...",
                delete_after=10,
            )
        game_vars.seeking_substr = ""


    async def complete_puzzle(
        self,
        announce: discord.Message,
        channel: discord.TextChannel,
        game_vars: GameVars,
        coin_value: int,
        bonus_value: int,
        msg: discord.Message,
        elapsed_time: float,
        bonus: bool,
        anarchy_override: bool,
        victim: str | discord.User,
    ) -> None:
        await announce.delete()
        await msg.add_reaction("👍")

        outcome = finish_bomb(game_vars, anarchy_override, bonus, bonus_value, msg.author.id, coin_value)
        spawn_msgs = {
            1: f"{msg.author} got it (took {elapsed_time:.2f} sec), so their money will be left alone.  `{msg.content.lower()}` has now been added to the list of used words.",
            2: f"{msg.author} got it (took {elapsed_time:.2f} sec), and {coin_value}$ has been split between the bank and their wallet, out of {victim}'s wallet!  `{msg.content.lower()}` has now been added to the list of used words.",
            3: f"{msg.author} got it (took {elapsed_time:.2f} sec), and {coin_value + bonus_value}$ has been deposited into their wallet!  The economy has just grown by {bonus_value}$!  `{msg.content.lower()}` has now been added to the list of used words.",
            4: f"{msg.author} got it (took {elapsed_time:.2f} sec), and {coin_value}$ has been deposited into their wallet!  `{msg.content.lower()}` has now been added to the list of used words.",
        }

        await channel.send(spawn_msgs[outcome], delete_after=10)

        timer_board_add(msg.author.id, elapsed_time, msg.content.lower(), game_vars.seeking_substr)
        add_used_word(msg.content.lower())
        game_vars.seeking_substr = ""
