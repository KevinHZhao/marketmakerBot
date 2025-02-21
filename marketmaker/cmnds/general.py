from __future__ import annotations

import math
import random
from functools import partial
from typing import Literal, Optional

import discord
from discord.ext import commands

from marketmaker.backend.db import (
    build_ledger,
    build_timetrial,
    fetch_used_words,
    fetch_wallet_amount,
)
from marketmaker.used_menus import MyMenuPages, MySource


class General(commands.Cog):
    def __init__(self: General, bot) -> None:
        self.bot = bot


    @commands.hybrid_command(name="wallet")
    async def cmd_wallet(self: General, ctx, target: discord.Member = None) -> None:
        """
        Displays a selected user's wallet.  Defaults to command user.
        """
        if target is None:
            target = ctx.author
        money = fetch_wallet_amount(target.id)
        await ctx.send(f"{target} has {money}$ in their wallet!")


    @commands.hybrid_command(name="used")
    async def cmd_used(self: General, ctx) -> None:
        """
        Displays all previously used words in the game.
        """
        used_words = sorted(fetch_used_words())
        num_used = len(used_words)
        wpp = 30 # words per page

        words_strings = [""] * math.ceil(num_used/wpp)
        for i, word in zip(range(num_used), used_words, strict=False):
            words_strings[i//wpp] += "`" + word + "`, "

        words_strings = [string[:-2] + "." for string in words_strings]

        formatter = MySource(words_strings, per_page = 1)
        menu = MyMenuPages(formatter)
        await menu.start(ctx)


    @commands.hybrid_command(name="bank")
    async def cmd_bank(self: General, ctx) -> None:
        """
        Displays the current money in the bank and the total money in the economy.
        """
        bank_money = fetch_wallet_amount("BANK")
        total_money = fetch_wallet_amount("TOTAL")
        await ctx.send(
            f"The bank currently has {bank_money}$, out of a total of {total_money}$ in the economy!"
        )


    @commands.hybrid_command(name="send")
    async def cmd_send(self: General, ctx, receiver: discord.Member, amount: int) -> None:
        """
        Sends a user an amount of money.
        """
        eco = self.bot.get_cog("Economy")
        try:
            if int(amount) > 0:
                if receiver.bot:
                    result = await eco.wallet_transfer(
                        ctx.author, "BANK", int(amount), ctx.channel, 5
                    )
                    await ctx.send(
                        f"{ctx.author.mention}, you're only supposed to use this command with non-bots...  Don't worry, we know you want to be generous, so your {result}$ has been sent to the bank!"
                    )
                else:
                    result = await eco.wallet_transfer(
                        ctx.author, receiver, int(amount), ctx.channel, 5
                    )
                    await ctx.send(
                        f"{receiver.mention}, {ctx.author.mention} has graciously sent you {result}$!"
                    )
            else:
                await ctx.send("Error, please enter a positive, integer amount.")
        except ValueError:
            await ctx.send("Error, please enter a valid amount.")


    @commands.hybrid_command(name="leaderboard")
    async def cmd_leaderboard(self: General, ctx) -> None:
        """
        Displays a leaderboard of up to ten users based on their current wallet.
        """
        lb = self.bot.get_cog("Leaderboard")
        board = await lb.build_leaderboard()
        print(board)
        if board is None:
            await ctx.channel.send("Nobody on the leaderboard!")
        else:
            await ctx.send(board)


    @commands.hybrid_command(name="ledger")
    async def cmd_ledger(self: General, ctx, target: discord.Member = None) -> None:
        """
        Displays a ledger of the ten most recent transactions from an individual
        """

        if isinstance(target, discord.User | discord.Member):
            targetid: Literal["BANK"] | int = target.id
        elif target is not None:
            raise Exception("target is neither discord.User nor None!")
        else:
            targetid = "BANK"
            await ctx.send(
                "No user given, showing ten most recent transactions...", delete_after=10
            )

        rows = build_ledger(targetid)

        if not rows:
            await ctx.send("User has no transactions!")
            return

        ledger = ""
        transaction_dict = {
            1: " for solving a bonus puzzle!",  # bonus puzzle
            2: " for solving a puzzle.",  # puzzle
            3: ", who was a victim of an anarchy puzzle.",  # anarchy puzzle
            4: " due to unethical behaviour.",  # cheat
            5: " as a donation.",  # send/donate
            6: " as taxes.",  # tax
            7: " as a wager.",  # random
            8: " as a bonus.",  # force_inflation
            9: " due to deflation.",  # force_deflataion
        }

        for row in rows:
            timestamp = row[0].split(".")[0]

            sendid = row[1]
            if sendid == "BANK":
                sender: Literal["the bank"] | discord.Member | None = "the bank"
            elif sendid == "N/A":
                sender = None
            else:
                sender = await self.bot.fetch_user(int(sendid))

            recid = row[2]
            if recid == "BANK":
                receiver: Literal["The bank"] | discord.Member = "The bank"
            else:
                receiver = await self.bot.fetch_user(int(recid))

            amount = row[3]
            transaction = row[4]

            if transaction in [1, 8]:
                ledger += f"[{timestamp}] {receiver} received {amount}${transaction_dict[transaction]}\n"
            elif transaction == 9:
                ledger += f"[{timestamp}] {receiver} lost {-amount}${transaction_dict[transaction]}\n"
            else:
                ledger += f"[{timestamp}] {receiver} received {amount}$ from {sender}{transaction_dict[transaction]}\n"

        await ctx.send(ledger)


    @commands.hybrid_command(name="random")
    async def cmd_random_event(self: General, ctx, wager: Optional[int] = None) -> None:
        """
        Causes a random event to occur, requires a wager rom the user.
        """
        if wager <= 0:
            await ctx.send(
                f"{ctx.author.mention}, you must provide a positive integer wager!"
            )
            return

        if self.bot.game_vars.seeking_substr != "":
            await ctx.send(
                f"{ctx.author.mention}, wait for the current puzzle to end before using this command!"
            )
            return

        user_money = fetch_wallet_amount(ctx.author.id)
        assert isinstance(wager, int)
        if wager > user_money:
            await ctx.send(
                f"{ctx.author.mention}, you don't have enough money for that wager!"
            )
            return

        eco = self.bot.get_cog("Economy")
        await eco.wallet_transfer(ctx.author, "BANK", wager, ctx.channel, 7)

        await ctx.send(f"{ctx.author.mention}, your wager of {wager}$ has been accepted by the bank.  Now rolling the dice...")

        user_money = fetch_wallet_amount(ctx.author.id)
        bank_money = fetch_wallet_amount("BANK")

        puzzle = self.bot.get_cog("Puzzle")
        all_puzzle = partial(puzzle.spawn_puzzle, channel = ctx.channel, game_vars = self.bot.game_vars, anarchy_override = True, anarchy_victim = ctx.author)
        normal_puzzle = partial(puzzle.spawn_puzzle, channel = ctx.channel, game_vars = self.bot.game_vars)

        buffed_value = min(math.ceil(wager*1.5), bank_money - 1)
        buffed_puzzle = partial(puzzle.spawn_puzzle, channel = ctx.channel, game_vars = self.bot.game_vars, coin_value = buffed_value, bonus_value = 500)

        deflation = partial(eco.force_deflation, channel = ctx.channel, user = ctx.author, amount = math.ceil(wager*2/3))
        inflation = partial(eco.force_inflation, channel = ctx.channel, user = ctx.author, amount = math.ceil(wager/2))
        dono = min(math.ceil(wager/2), user_money)
        bank_donation = partial(eco.donation, channel = ctx.channel, sender = ctx.author, receiver = "BANK", amount = dono)

        anarchy = partial(eco.force_anarchy, channel = ctx.channel, game_vars = self.bot.game_vars)
        taxation = partial(eco.tax, channel = ctx.channel)

        funf = self.bot.get_cog("Fun")
        history = [msg async for msg in ctx.channel.history(limit = 5)]
        fish = partial(funf.fish_react, message = random.choice(history))

        funcs = [all_puzzle, normal_puzzle, buffed_puzzle, anarchy, deflation, inflation, bank_donation, taxation, fish]

        # Create weights for funcs depending on wager
        if wager < 100:
            weights = (0.05, 0.1, 0.02, 0.03, 0.025, 0.025, 0.4, 0.05, 0.3)
        elif 100 <= wager < 250:
            weights = (0.04, 0.15, 0.15, 0.05, 0.04, 0.04, 0.23, 0.05, 0.25)
        elif 250 <= wager < 500:
            weights = (0.03, 0.1, 0.3, 0.07, 0.08, 0.08, 0.16, 0.03, 0.15)
        elif 500 <= wager < 1000:
            weights = (0.02, 0.1, 0.4, 0.07, 0.08, 0.08, 0.13, 0.02, 0.1)
        else:
            weights = (0.01, 0, 0.6, 0.11, 0.13, 0.13, 0, 0, 0.02)

        selected_fun = random.choices(funcs, weights=weights, k=1)[0]

        await selected_fun()


    @commands.hybrid_command(name="timetrial")
    async def cmd_timetrial(self: General, ctx) -> None:
        """
        Shows a leaderboard of fastest solves, resets every day.
        """
        rows = build_timetrial()

        if not rows:
            await ctx.send("Nobody on the leaderboard!")
            return

        board = ""
        awards = {0 : "🥇", 1 : "🥈", 2 : "🥉"}
        for row, i in zip(rows, range(len(rows))):
            board += f"{awards[i]} {await self.bot.fetch_user(row[0])} {awards[i]}: {row[1]:.2f} sec, answering `{row[2]}` for `{row[3]}`.\n"

        await ctx.send(board)


    @commands.hybrid_command(name="force_tax")
    async def cmd_force_tax(self: General, ctx) -> None:
        """
        Developer command, forces taxation on all users.
        """
        if self.bot.dev:
            eco = self.bot.get_cog("Economy")
            await eco.tax(ctx.channel)
        else:
            await ctx.send("No.")


    @commands.hybrid_command(name="cheat")
    async def cmd_cheat(self: General, ctx) -> None:
        """
        Developer command, steals 99% of the bank's money and deposits it in user's wallet.
        """
        eco = self.bot.get_cog("Economy")
        if self.bot.dev:
            bank_money = fetch_wallet_amount("BANK")
            await eco.wallet_transfer("BANK", ctx.author, math.ceil(0.99 * bank_money), ctx.channel, 4)
            await ctx.send("Cheat successful!")
        else:
            result = await eco.wallet_transfer(ctx.author, "BANK", 5, ctx.channel, 4)
            await ctx.send(
                f"{ctx.author.mention}, you have successfully donated {result}$ to the bank, good job!"
            )
