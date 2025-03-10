from __future__ import annotations

import asyncio
import datetime
import math
import random
from functools import partial
from typing import TYPE_CHECKING

from discord.ext import commands

from marketmaker.backend.bomb_party import check_bomb, finish_bomb, setup_bomb
from marketmaker.backend.db import (
    add_used_word,
    bonus_transfer,
    fetch_used_words,
    fetch_wallet_amount,
    generate_victim,
    timer_board_add,
)
from marketmaker.backend.letter_bowl import LetterBowlBackend
from marketmaker.backend.phrase_hangman import HangmanBackend

if TYPE_CHECKING:
    import discord

    from marketmaker.subclass import GameVars


class Puzzle(commands.Cog):
    def __init__(self: Puzzle, bot) -> None:
        self.bot = bot
        self.lock = asyncio.Lock()
        self.coin_value = 0
        self.anarchy_override = False
        self.outcome: None | int = None
        self.lb = LetterBowlBackend()
        self.ph = HangmanBackend()
        self.bonus = False


    def is_puzzle_running(self:Puzzle) -> bool:
        return self.lock.locked()


    async def spawn_ph(
        self: Puzzle,
        vicmen: discord.mentions,
        game_vars: GameVars,
        victim: discord.Member,
        channel: discord.TextChannel,
        bonus_value: int,
    ):
        self.ph.begin_puzzle()
        time_lim = 15

        def gen_msg(time_left) -> dict:
            return {
                1: f"{vicmen}, all {self.coin_value}$ from your wallet has spawned, unlucky!  Anyone can claim them by deciphering this {self.ph.phrase_type.lower()} within {time_left} seconds:\n`{self.ph.guide.lower()}`",
                2: f"The bank's looking pretty empty, so instead, :coin: Coins :coin: from {victim}'s wallet have spawned, valued at {self.coin_value}$!  You can claim them by deciphering this {self.ph.phrase_type.lower()} within {time_left} seconds:\n`{self.ph.guide.lower()}`",
                3: f":dollar: Bonus Coins :dollar: have spawned, valued at {self.coin_value}$ plus another {bonus_value}$ as bonus!  You can claim them by deciphering this {self.ph.phrase_type.lower()} within {time_left} seconds:\n`{self.ph.guide.lower()}`",
                4: f":coin: Coins :coin: from the bank have spawned, valued at {self.coin_value}$!  You can claim them by deciphering this {self.ph.phrase_type.lower()} within {time_left} seconds:\n`{self.ph.guide.lower()}`",
            }

        results: tuple | None | int = 0
        winmsg = None
        for i in [4, 3, 2, 1]:
            time_left = time_lim * i
            announce = await channel.send(gen_msg(time_left)[self.outcome], delete_after=time_lim)
            results = await self.test_ph(channel, announce, time_lim)
            if results is not None:
                winmsg, elapsed_time = results
                await announce.delete()
                break
            self.ph.build_guide()

        if winmsg is None:
            await channel.send(f"The phrase was `{self.ph.answer}`!", delete_after=10)
            await self.failed(game_vars, channel)
        else:
            await winmsg.add_reaction("👍")
            if round(elapsed_time % 10, 2) == 7.27:
                bonus_transfer(winmsg.author.id, 727)
                await channel.send(f"WYSI buff applied, {winmsg.author} has received 727$ from out of thin air as a bonus.")
            await self.complete_ph(channel, game_vars, bonus_value, winmsg, elapsed_time, victim)


    async def complete_ph(
        self,
        channel: discord.TextChannel,
        game_vars: GameVars,
        bonus_value: int,
        msg: discord.Message,
        elapsed_time: float,
        victim: str | discord.Member,
    ) -> None:
        if game_vars.victimid:
            self.ph.finish(self.coin_value, msg.author.id, bonus_value * self.bonus, game_vars.victimid)
        else:
            self.ph.finish(self.coin_value, msg.author.id, bonus_value * self.bonus)
        spawn_msgs = {
            1: f"{msg.author} got it (took {elapsed_time:.2f} sec after the last hint), so their money will be left alone.",
            2: f"{msg.author} got it (took {elapsed_time:.2f} sec after the last hint), and {self.coin_value}$ has been split between them and the bank, out of {victim}'s wallet!",
            3: f"{msg.author} got it (took {elapsed_time:.2f} sec after the last hint), and {self.coin_value + bonus_value}$ has been deposited into their wallet!  The economy has just grown by {bonus_value}$!",
            4: f"{msg.author} got it (took {elapsed_time:.2f} sec after the last hint), and {self.coin_value}$ has been deposited into their wallet!",
        }
        if game_vars.anarchy or self.anarchy_override:
            res = 2 if game_vars.victimid != msg.id else 1
        else:
            res = 3 if self.bonus else 4

        await channel.send(spawn_msgs[res], delete_after=10)

        game_vars.victimid = None
        self.coin_value = 0
        self.outcome = None
        self.bonus = False


    async def test_ph(
        self,
        channel: discord.TextChannel,
        announce: discord.Message,
        time_lim: float
    ) -> tuple[discord.Message, float] | None:
        def check(m: discord.Message) -> bool:
            if not m.content:
                return False
            return self.ph.check(m.content.lower()) and m.channel == channel

        start_time = announce.created_at
        elapsed_time = 0.0
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=time_lim)
            elapsed_time = (datetime.datetime.now(datetime.UTC) - start_time).total_seconds()
        except TimeoutError:
            return None

        return (msg, elapsed_time)


    async def spawn_lb(
        self: Puzzle,
        vicmen: discord.mentions,
        game_vars: GameVars,
        victim: discord.Member,
        channel: discord.TextChannel,
        bonus_value: int,
    ):
        self.lb.restart()

        letters = ", ".join(self.lb.letters)
        time_lim = random.randrange(20, 60)

        spawn_msgs = {
            1: f"{vicmen}, all {self.coin_value}$ from your wallet has spawned, unlucky!  Anyone can claim some of them by typing a word using only the letters `{letters}` within {time_lim} seconds!",
            2: f"The bank's looking pretty empty, so instead, :coin: Coins :coin: from {victim}'s wallet have spawned, valued at {self.coin_value}$!  You can claim some of them by typing a word using only the letters `{letters}` within {time_lim} seconds!",
            3: f":dollar: Bonus Coins :dollar: have spawned, valued at {self.coin_value}$ plus another {bonus_value}$ per word in the streak!  You can claim some of them by typing a word using only the letters `{letters}` within {time_lim} seconds!",
            4: f":coin: Coins :coin: from the bank have spawned, valued at {self.coin_value}$!  You can claim some of them by typing a word with only the letters `{letters}` within {time_lim} seconds!",
        }

        announce = await channel.send(spawn_msgs[self.outcome], delete_after=time_lim)
        results: tuple | None | int = 0
        winmsg = None
        while results is not None:
            results = await self.test_lb(channel, announce, time_lim)
            if results is not None:
                winmsg, elapsed_time = results
                await announce.delete()
                await winmsg.add_reaction("👍")
                time_lim = random.randrange(20, 60)
                announce = await channel.send(f"{winmsg.author} got it using {len(winmsg.content)} letters (took {elapsed_time:.2f} sec).  Anyone can increase the winnings and take the prize by typing a longer word using only the letters `{letters}` within {time_lim} seconds!", delete_after=time_lim)
                if round(elapsed_time % 10, 2) == 7.27:
                    bonus_transfer(winmsg.author.id, 727)
                    await channel.send(f"WYSI buff applied, {winmsg.author} has received 727$ from out of thin air as a bonus.")

        if winmsg is None:
            await self.failed(game_vars, channel)
        else:
            await self.complete_lb(channel, game_vars, bonus_value, winmsg, elapsed_time, victim)


    async def complete_lb(
        self,
        channel: discord.TextChannel,
        game_vars: GameVars,
        bonus_value: int,
        msg: discord.Message,
        elapsed_time: float,
        victim: str | discord.Member,
    ) -> None:
        if game_vars.victimid:
            score, to_winner, bonus_prize = self.lb.finish(self.coin_value, msg.author.id, bonus_value * self.bonus, game_vars.victimid)
        else:
            score, to_winner, bonus_prize = self.lb.finish(self.coin_value, msg.author.id, bonus_value * self.bonus)
        spawn_msgs = {
            1: f"Time's up!  {msg.author} is our winner after a streak of {score} words (took {elapsed_time:.2f} sec), so their money will be left alone.",
            2: f"Time's up!  {msg.author} is our winner after a streak of {score} words (took {elapsed_time:.2f} sec), and {to_winner}$ has been sent their wallet out of {victim}'s wallet, with the remainder of the {self.coin_value}$ prize pool going to the bank!",
            3: f"Time's up!  {msg.author} is our winner after a streak of {score} words (took {elapsed_time:.2f} sec), and {to_winner + bonus_prize}$ has been deposited into their wallet!  The economy has just grown by {bonus_prize}$!",
            4: f"Time's up!  {msg.author} is our winner after a streak of {score} words (took {elapsed_time:.2f} sec), and {to_winner}$ has been deposited into their wallet!",
        }
        if game_vars.anarchy or self.anarchy_override:
            res = 2 if game_vars.victimid != msg.id else 1
        else:
            res = 3 if self.bonus else 4

        await channel.send(spawn_msgs[res], delete_after=10)

        game_vars.victimid = None
        self.coin_value = 0
        self.outcome = None
        self.bonus = False


    async def test_lb(
        self,
        channel: discord.TextChannel,
        announce: discord.Message,
        time_lim: float
    ) -> tuple[discord.Message, float] | None:
        def check(m: discord.Message) -> bool:
            if not m.content:
                return False
            return self.lb.check_word(m.content.lower()) and m.channel == channel

        start_time = announce.created_at
        elapsed_time = 0.0
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=time_lim)
            elapsed_time = (datetime.datetime.now(datetime.UTC) - start_time).total_seconds()
        except TimeoutError:
            return None

        self.lb.increment(msg.content)

        return (msg, elapsed_time)


    def setup_coin(self:Puzzle, game_vars: GameVars, anarchy_victim: discord.Member):
        bank_money = fetch_wallet_amount("BANK")
        if self.anarchy_override:
            game_vars.victimid = anarchy_victim.id
            self.coin_value = fetch_wallet_amount(anarchy_victim.id)
            self.outcome = 1
        elif game_vars.anarchy:
            game_vars.victimid, victim_money = generate_victim()
            game_vars.victimid = int(game_vars.victimid)
            self.coin_value = random.randrange(1, math.ceil(victim_money / 4 + 1))
            self.outcome = 2
        else:
            if self.coin_value is None:
                self.coin_value = random.randrange(1, math.ceil(bank_money / 6 + 10))
            if self.bonus:
                print("BONUS TIME")
                self.outcome = 3
            else:
                self.outcome = 4


    async def spawn_bp(
        self:Puzzle,
        vicmen:discord.mentions,
        game_vars:GameVars,
        victim:discord.Member,
        channel:discord.TextChannel,
        bonus_value:int,
    ):
        setup_bomb(game_vars, self.bonus, self.bot.normal_min_words, self.bot.hard_min_words)

        spawn_msgs = {
            1: f"{vicmen}, all {self.coin_value}$ from your wallet has spawned, unlucky!  Anyone can claim them by typing a word with `{game_vars.seeking_substr}` within 30 seconds!",
            2: f"The bank's looking pretty empty, so instead, :coin: Coins :coin: from {victim}'s wallet have spawned, valued at {self.coin_value}$!  You can claim them by typing a word with `{game_vars.seeking_substr}` within 30 seconds!",
            3: f":dollar: Bonus Coins :dollar: have spawned, valued at {self.coin_value + bonus_value}$!  You can claim them by typing a word with `{game_vars.seeking_substr}` within 30 seconds!",
            4: f":coin: Coins :coin: from the bank have spawned, valued at {self.coin_value}$!  You can claim them by typing a word with `{game_vars.seeking_substr}` within 30 seconds!",
        }

        announce = await channel.send(spawn_msgs[self.outcome], delete_after=30)
        results = await self.test_bp(channel, game_vars, announce)

        if results is None:
            await self.failed(game_vars, channel)
        else:
            answer, elapsed_time = results

            if round(elapsed_time % 10, 2) == 7.27:
                extra_bonus = round(bonus_value * 7.27)
                bonus_value = bonus_value * self.bonus + extra_bonus
                self.bonus = True
                await channel.send(f"WYSI buff applied, extra bonus applied to this puzzle of {extra_bonus}$.")
            await self.complete_bp(
                announce,
                channel,
                game_vars,
                bonus_value,
                answer,
                elapsed_time,
                victim,
            )


    async def spawn_puzzle(
        self: Puzzle,
        channel: discord.TextChannel,
        game_vars: GameVars,
        coin_value: int | None = None,
        bonus_value: int = 500,
        anarchy_override: bool = False,
        anarchy_victim: discord.Member = None,
    ) -> None:
        if self.lock.locked():
            await channel.send("Error: Somehow tried to spawn a puzzle while one was already active.  Please report this to the bot owner.")
            return

        async with self.lock:
            bank_money = fetch_wallet_amount("BANK")
            total_money = fetch_wallet_amount("TOTAL")
            self.anarchy_override = anarchy_override

            if game_vars.anarchy:
                game_vars.anarchy = bank_money < total_money / 5
            else:
                game_vars.anarchy = bank_money < total_money / 90

            if self.anarchy_override and fetch_wallet_amount(anarchy_victim.id) == 0:
                await channel.send(
                    f"We were going to put all of {anarchy_victim.mention}'s money up for a puzzle, but they don't have any left!  Nothing happens...",
                )
                return

            self.bonus = random.randrange(10) < 3

            self.coin_value = coin_value

            self.setup_coin(game_vars, anarchy_victim)
            if game_vars.victimid is None:
                # This is a failsafe, but it should never be reached
                victim = "ERROR NO VICTIM"
                vicmen = "ERROR NO VICTIM"
            else:
                if self.anarchy_override:
                    victim = anarchy_victim
                    game_vars.victimid = anarchy_victim.id
                else:
                    victim = await self.bot.fetch_user(game_vars.victimid)

                game_vars.anarchy = True
                vicmen = victim.mention

            bp = partial(self.spawn_bp, vicmen, game_vars, victim, channel, bonus_value * 2)
            lb = partial(self.spawn_lb, vicmen, game_vars, victim, channel, bonus_value)
            ph = partial(self.spawn_ph, vicmen, game_vars, victim, channel, bonus_value * 2)
            weights = (1/3, 1/3, 1/3)

            funcs = [bp, lb, ph]
            selected_fun = random.choices(funcs, weights = weights, k = 1)[0]

            await selected_fun()


    async def test_bp(
        self,
        channel: discord.TextChannel,
        game_vars: GameVars,
        announce: discord.Message,
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

        start_time = announce.created_at
        TIME_LIMIT_SEC = 30.0
        elapsed_time = 0.0
        try:
            # Keep listening for messages until 30 seconds have passed or a 👍 reaction is given
            while elapsed_time < TIME_LIMIT_SEC:
                try:
                    # Wait for a message (1 second timeout for each check)
                    msg = await self.bot.wait_for("message", check=check, timeout=1.0)

                    elapsed_time = (datetime.datetime.now(datetime.UTC) - start_time).total_seconds()

                    # If the message is in used_words, react with ❌ and continue checking
                    if msg.content.lower() in used_words:
                        await msg.add_reaction("❌")
                    else:
                        break  # End the game when a valid message is found

                except TimeoutError:
                    elapsed_time = (datetime.datetime.now(datetime.UTC) - start_time).total_seconds()
                    continue  # If no new message, continue the loop

            if elapsed_time >= TIME_LIMIT_SEC:
                raise TimeoutError
        except TimeoutError:
            return None

        return (msg, elapsed_time)


    async def failed(
        self: Puzzle,
        game_vars: GameVars,
        channel: discord.TextChannel,
    ) -> None:
        if game_vars.anarchy:
            assert game_vars.victimid is not None
            victim = await self.bot.fetch_user(game_vars.victimid)
            await channel.send(
                f"Time's up!  No one claimed the :coin: Coins :coin: so {victim}'s {self.coin_value}$ are going to the bank!",
                delete_after=10,
            )
            eco = self.bot.get_cog("Economy")
            await eco.wallet_transfer(victim, "BANK", self.coin_value, channel, 3)
            game_vars.victimid = None
            game_vars.anarchy = False
        else:
            await channel.send(
                "Time's up!  No one claimed the :coin: Coins :coin: so they've been returned to the bank...",
                delete_after=10,
            )
        game_vars.seeking_substr = ""
        self.coin_value = 0
        game_vars.victimid = None
        self.outcome = None
        self.bonus = False


    async def complete_bp(
        self,
        announce: discord.Message,
        channel: discord.TextChannel,
        game_vars: GameVars,
        bonus_value: int,
        msg: discord.Message,
        elapsed_time: float,
        victim: str | discord.Member,
    ) -> None:
        await announce.delete()
        await msg.add_reaction("👍")

        outcome = finish_bomb(game_vars, self.anarchy_override, self.bonus, bonus_value, msg.author.id, self.coin_value)
        spawn_msgs = {
            1: f"{msg.author} got it (took {elapsed_time:.2f} sec), so their money will be left alone.  `{msg.content.lower()}` has now been added to the list of used words.",
            2: f"{msg.author} got it (took {elapsed_time:.2f} sec), and {self.coin_value}$ has been split between the bank and their wallet, out of {victim}'s wallet!  `{msg.content.lower()}` has now been added to the list of used words.",
            3: f"{msg.author} got it (took {elapsed_time:.2f} sec), and {self.coin_value + bonus_value}$ has been deposited into their wallet!  The economy has just grown by {bonus_value}$!  `{msg.content.lower()}` has now been added to the list of used words.",
            4: f"{msg.author} got it (took {elapsed_time:.2f} sec), and {self.coin_value}$ has been deposited into their wallet!  `{msg.content.lower()}` has now been added to the list of used words.",
        }

        await channel.send(spawn_msgs[outcome], delete_after=10)

        timer_board_add(msg.author.id, elapsed_time, msg.content.lower(), game_vars.seeking_substr)
        add_used_word(msg.content.lower())
        game_vars.seeking_substr = ""
        game_vars.victimid = None
        self.coin_value = 0
        self.outcome = None
        self.bonus = False
