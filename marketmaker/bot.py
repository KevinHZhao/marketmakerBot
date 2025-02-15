from __future__ import annotations

import asyncio
import datetime
import math
import os
import random
import sqlite3
from pathlib import Path
from typing import Literal, Union

import discord
import enchant
from discord.ext import commands, tasks
from dotenv import load_dotenv

from marketmaker.backend import used_words_backend, wallet_backend
from marketmaker.initialization import ensure_db, ensure_substr

dict = enchant.Dict("en_CA")

load_dotenv()

# Setup
BOT_TOKEN = os.getenv("BOT_TOKEN")

prob_coin = int(os.getenv("PROB"))
dev = bool(int(os.getenv("DEV_MODE")))

# Game data init
ensure_substr()
ensure_db()

# Constants
seeking_substr = ""
victim = ""
anarchy = False
daily_counter = 3

time = datetime.time(hour=5, minute=0, tzinfo=datetime.UTC)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="##", intents=intents)


def bonus_transfer(receiver: Union[discord.User, Literal["BANK"]], amount: int) -> None:
    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()

    recid: Literal["BANK"] | int = receiver.id if receiver != "BANK" else "BANK"

    receiver_cash = wallet_backend(recid)
    total_cash = wallet_backend("TOTAL")

    cur.execute(
        "UPDATE wallets SET cash = ? WHERE ID = ?", (receiver_cash + amount, recid)
    )
    cur.execute(
        "UPDATE wallets SET cash = ? WHERE ID = ?", (total_cash + amount, "TOTAL")
    )

    economy.commit()
    economy.close()
    print(f"Gave {amount} to {receiver} as a bonus.")


async def wallet_transfer(
    sender: Union[discord.User, Literal["BANK", "TOTAL"]],
    receiver: Union[discord.User, Literal["BANK", "TOTAL"]],
    amount: int,
    channel: discord.TextChannel,
) -> int:
    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()
    if sender == "TOTAL" or receiver == "TOTAL":
        raise Exception("TOTAL entered for sender/receiver!")

    recid: Literal["BANK"] | int = receiver.id if receiver != "BANK" else "BANK"
    sendid: Literal["BANK"] | int = sender.id if sender != "BANK" else "BANK"

    sender_cash = wallet_backend(sendid)

    if sender_cash < amount:
        if sender == "BANK":
            sendmen = "The bank"
        else:
            sendmen = sender.mention

        if receiver == "BANK":
            recmen = "the bank"
        else:
            recmen = receiver.mention

        await channel.send(
            f"{sendmen} somehow doesn't have enough cash, so we'll just send all of their {sender_cash}$ to {recmen}."
        )
        cur.execute("UPDATE wallets SET cash = ? WHERE ID = ?", (0, sendid))

        economy.commit()
        receiver_cash = wallet_backend(recid)

        cur.execute(
            "UPDATE wallets SET cash = ? WHERE ID = ?",
            (receiver_cash + sender_cash, recid),
        )
        result = sender_cash
    else:
        cur.execute(
            "UPDATE wallets SET cash = ? WHERE ID = ?", (sender_cash - amount, sendid)
        )

        economy.commit()
        receiver_cash = wallet_backend(recid)

        cur.execute(
            "UPDATE wallets SET cash = ? WHERE ID = ?", (receiver_cash + amount, recid)
        )
        result = amount

    economy.commit()
    economy.close()
    print(f"Transferred {result} from {sender} to {receiver}.")
    return result


async def spawn_puzzle(channel: discord.TextChannel) -> None:
    global victim
    global anarchy
    global daily_counter
    global seeking_substr

    bank_money = wallet_backend("BANK")
    total_money = wallet_backend("TOTAL")
    used_words = used_words_backend()

    if anarchy:
        anarchy = bank_money < total_money / 5
    else:
        anarchy = bank_money < total_money / 90

    root = Path(__file__).parents[1]

    normal_min_words = int(os.getenv("NORMAL_MIN_WORDS"))
    with open(f"{root}/static/substr_normal_{normal_min_words}.txt", "r") as f:
        normal_substrings = [line.rstrip("\n") for line in f]

    seeking_substr = random.choice(normal_substrings)
    if anarchy:
        economy = sqlite3.connect("marketmaker.db")
        cur = economy.cursor()

        cur.execute("""
        SELECT ID, cash
        FROM wallets
        WHERE ID NOT IN ("BANK", "TOTAL") AND cash > 1            
        """)
        rows = cur.fetchall()
        victim_row = random.choice(rows)
        victim = await bot.fetch_user(victim_row[0])
        victim_money = victim_row[1]
        economy.close()

        coin_value = random.randrange(1, math.ceil(victim_money / 4 + 1))
        announce = await channel.send(
            f"The bank's looking pretty empty, so instead, :coin: Coins :coin: from {victim.mention}'s wallet have spawned, valued at {coin_value}$!  You can claim them by typing a word with `{seeking_substr}` within 30 seconds!",
            delete_after=30,
        )
    else:
        coin_value = random.randrange(1, math.ceil(bank_money / 6 + 10))
        if daily_counter > 0 and random.randrange(10) == 9:
            print("BONUS TIME")

            hard_min_words = int(os.getenv("HARD_MIN_WORDS"))
            with open(f"{root}/static/substr_hard_{hard_min_words}.txt", "r") as f:
                hard_substrings = [line.rstrip("\n") for line in f]

            seeking_substr = random.choice(hard_substrings)
            announce = await channel.send(
                f":dollar: Bonus Coins :dollar: have spawned, valued at {coin_value + 100}$!  You can claim them by typing a word with `{seeking_substr}` within 30 seconds!",
                delete_after=30,
            )
            bonus = True
            daily_counter -= 1
        else:
            announce = await channel.send(
                f":coin: Coins :coin: from the bank have spawned, valued at {coin_value}$!  You can claim them by typing a word with `{seeking_substr}` within 30 seconds!",
                delete_after=30,
            )
            bonus = False

    def check(m):
        if not m.content:
            return False
        return (
            not m.author.bot
            and dict.check(m.content.lower())
            and seeking_substr in m.content.lower()
            and m.channel == channel
        )

    start_time = datetime.datetime.now()
    TIME_LIMIT_SEC = 30
    elapsed_time = 0
    try:
        # Keep listening for messages until 30 seconds have passed or a 👍 reaction is given
        while elapsed_time < TIME_LIMIT_SEC:
            try:
                # Wait for a message (1 second timeout for each check)
                msg = await bot.wait_for("message", check=check, timeout=1.0)

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
        if anarchy:
            await channel.send(
                f"Time's up!  No one claimed the :coin: Coins :coin: so {victim.mention}'s {coin_value}$ are going to the bank!",
                delete_after=10,
            )
            await wallet_transfer(victim, "BANK", coin_value, channel)
        else:
            await channel.send(
                "Time's up!  No one claimed the :coin: Coins :coin: so they've been returned to the bank...",
                delete_after=10,
            )
        seeking_substr = ""
        return

    await announce.delete()
    await msg.add_reaction("👍")
    if anarchy:
        if victim == msg.author:
            await channel.send(
                f"{msg.author.mention} got it, so their money will be left alone.  `{msg.content.lower()}` has now been added to the list of used words.",
                delete_after=10,
            )
        else:
            await channel.send(
                f"{msg.author.mention} got it, and {coin_value}$ has been split between the bank and their wallet, out of {victim.mention}'s wallet!  `{msg.content.lower()}` has now been added to the list of used words.",
                delete_after=10,
            )
            await wallet_transfer(
                victim, msg.author, math.ceil(coin_value / 2), channel
            )
            await wallet_transfer(victim, "BANK", math.floor(coin_value / 2), channel)
    else:
        if bonus:
            await channel.send(
                f"{msg.author.mention} got it, and {coin_value + 100}$ has been deposited into their wallet!  The economy has just grown by 100$!  `{msg.content.lower()}` has now been added to the list of used words.",
                delete_after=10,
            )
            bonus_transfer(msg.author, 100)
            bonus = False
        else:
            await channel.send(
                f"{msg.author.mention} got it, and {coin_value}$ has been deposited into their wallet!  `{msg.content.lower()}` has now been added to the list of used words.",
                delete_after=10,
            )
        await wallet_transfer("BANK", msg.author, coin_value, channel)

    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()
    cur.execute("INSERT INTO used_words VALUES (?)", (msg.content.lower(),))
    economy.commit()
    economy.close()
    seeking_substr = ""


@bot.event
async def on_ready() -> None:
    print(f"We have logged in as {bot.user}")
    print(bot.guilds)
    timed = bool(int(os.getenv("TIMED_SPAWN")))
    if timed:
        timed_puzzle.start()
    tax.start()
    await bot.tree.sync()


@bot.event
async def on_message(message) -> None:
    if message.author.bot:
        return

    await bot.process_commands(message)

    global seeking_substr

    if random.randrange(100) < prob_coin and not seeking_substr and message.guild:
        await spawn_puzzle(message.channel)


@tasks.loop(time=time)
async def tax() -> None:
    print("Taxation time!")

    global daily_counter
    daily_counter = 3

    channel = bot.get_channel(int(os.getenv("CHANNEL")))

    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()
    cur.execute("SELECT ID FROM wallets WHERE ID NOT IN ('BANK', 'TOTAL')")
    userids = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT cash FROM wallets WHERE ID NOT IN ('BANK', 'TOTAL')")
    moneys = [row[0] for row in cur.fetchall()]
    economy.close()

    for userid, money in zip(userids, moneys):
        user = await bot.fetch_user(userid)
        await wallet_transfer(user, "BANK", math.ceil(0.05 * money), channel)

    bank_money = wallet_backend("BANK")

    await channel.send(
        f"Taxation time!  The value of the bank is now {bank_money}$.  Good work everyone!"
    )


@tasks.loop(seconds=random.randint(60, 600))
async def timed_puzzle() -> None:
    channel = bot.get_channel(int(os.getenv("CHANNEL")))
    await spawn_puzzle(channel)


@bot.hybrid_command()
async def wallet(ctx, target: discord.User = None) -> None:
    """
    Displays a selected user's wallet.  Defaults to command user.
    """
    if target is None:
        target = ctx.author
    money = wallet_backend(target.id)
    await ctx.send(f"{target} has {money}$ in their wallet!")


@bot.hybrid_command()
async def used(ctx) -> None:
    """
    Displays all previously used words in the game.
    """
    used_words = used_words_backend()

    words_string = ""
    for word in used_words:
        words_string += "`" + word + "`, "
    words_string = words_string[:-2] + "."
    await ctx.send(words_string)


@bot.hybrid_command()
async def bank(ctx) -> None:
    """
    Displays the current money in the bank and the total money in the economy.
    """
    bank_money = wallet_backend("BANK")
    total_money = wallet_backend("TOTAL")
    await ctx.send(
        f"The bank currently has {bank_money}$, out of a total of {total_money}$ in the economy!"
    )


@bot.hybrid_command()
async def send(ctx, receiver: discord.User, amount: int) -> None:
    """
    Sends a user an amount of money.
    """
    try:
        if int(amount) > 0:
            if receiver.bot:
                result = await wallet_transfer(
                    ctx.author, "BANK", int(amount), ctx.channel
                )
                await ctx.send(
                    f"{ctx.author.mention}, you're only supposed to use this command with non-bots...  Don't worry, we know you want to be generous, so your {result}$ has been sent to the bank!"
                )
            else:
                result = await wallet_transfer(
                    ctx.author, receiver, int(amount), ctx.channel
                )
                await ctx.send(
                    f"{receiver.mention}, {ctx.author.mention} has graciously sent you {result}$!"
                )
        else:
            await ctx.send("Error, please enter a positive, integer amount.")
    except ValueError:
        await ctx.send("Error, please enter a valid amount.")


@bot.hybrid_command()
async def leaderboard(ctx) -> None:
    """
    Displays a leaderboard of up to ten users based on their current wallet.
    """
    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()

    cur.execute("""
    SELECT ID, cash
    FROM wallets
    WHERE ID NOT IN ("BANK", "TOTAL") AND cash > 0
    ORDER BY cash DESC
    LIMIT 10
    """)
    rows = cur.fetchall()
    if not rows:
        await ctx.send("Nobody on the leaderboard!")
        return

    board = ""
    for row, i in zip(rows, range(len(rows))):
        board += f"{i}. {await bot.fetch_user(row[0])}: {row[1]}$\n"

    await ctx.send(board)


@bot.hybrid_command()
async def force_tax(ctx) -> None:
    """
    Developer command, forces taxation on all users.
    """
    if dev:
        await tax()
    else:
        await ctx.send("No.")


@bot.hybrid_command()
async def cheat(ctx) -> None:
    """
    Developer command, steals 99% of the bank's money and deposits it in user's wallet.
    """
    if dev:
        bank_money = wallet_backend("BANK")
        await wallet_transfer(
            "BANK", ctx.author, math.ceil(0.99 * bank_money), ctx.channel
        )
        await ctx.send("Cheat successful!")
    else:
        result = await wallet_transfer(ctx.author, "BANK", 5, ctx.channel)
        await ctx.send(
            f"{ctx.author.mention}, you have successfully donated {result}$ to the bank, good job!"
        )


# Make the bot runnable from CLI (main must be a function)
def run_bot() -> None:
    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    # this allows you to run the bot from this script too
    run_bot()
