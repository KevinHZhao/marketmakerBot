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
from discord.ext import tasks
from dotenv import load_dotenv

from marketmaker.backend import used_words_backend, wallet_backend
from marketmaker.initialization import ensure_db, ensure_substr
from marketmaker.subclass import MarketmakerBot

dict = enchant.Dict("en_CA")

load_dotenv()

# Setup
BOT_TOKEN = os.getenv("BOT_TOKEN")

prob_coin = int(os.getenv("PROB"))
dev = bool(int(os.getenv("DEV_MODE")))

# Game data init
ensure_substr()
ensure_db()

time = datetime.time(hour=5, minute=0, tzinfo=datetime.UTC)

intents = discord.Intents.default()
intents.message_content = True

bot = MarketmakerBot(command_prefix="##", intents=intents)


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
    
    timestamp = datetime.datetime.now()
    
    cur.execute(
        "INSERT INTO ledger (time, sender, receiver, amount, type) VALUES (?, 'N/A', ?, ?, 1)",
        (timestamp, recid, amount)
    )

    economy.commit()
    economy.close()
    print(f"Gave {amount} to {receiver} as a bonus.")


async def wallet_transfer(
    sender: Union[discord.User, Literal["BANK"]],
    receiver: Union[discord.User, Literal["BANK"]],
    amount: int,
    channel: discord.TextChannel,
    transaction: int
) -> int:
    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()

    recid: Literal["BANK"] | int = receiver.id if isinstance(receiver, discord.User) else "BANK"
    sendid: Literal["BANK"] | int = sender.id if isinstance(sender, discord.User) else "BANK"

    sender_cash = wallet_backend(sendid)

    if sender_cash < amount:
        if isinstance(sender, discord.User):
            sendmen = sender.mention
        else:
            sendmen = "The bank"

        if isinstance(receiver, discord.User):
            recmen = receiver.mention
        else:
            recmen = "the bank"

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
    
    timestamp = datetime.datetime.now()
    
    cur.execute(
        "INSERT INTO ledger (time, sender, receiver, amount, type) VALUES (?, ?, ?, ?, ?)",
        (timestamp, sendid, recid, amount, transaction)
    )

    economy.commit()
    economy.close()
    print(f"Transferred {result} from {sender} to {receiver}.")
    return result


async def spawn_puzzle(channel: discord.TextChannel) -> None:
    victim = bot.game_vars.victim
    daily_counter = bot.game_vars.daily_counter

    bank_money = wallet_backend("BANK")
    total_money = wallet_backend("TOTAL")
    used_words = used_words_backend()

    if bot.game_vars.anarchy:
        bot.game_vars.anarchy = bank_money < total_money / 5
    else:
        bot.game_vars.anarchy = bank_money < total_money / 90

    root = Path(__file__).parents[1]

    normal_min_words = int(os.getenv("NORMAL_MIN_WORDS"))
    with open(f"{root}/static/substr_normal_{normal_min_words}.txt", "r") as f:
        normal_substrings = [line.rstrip("\n") for line in f]

    bot.game_vars.seeking_substr = random.choice(normal_substrings)
    if bot.game_vars.anarchy:
        economy = sqlite3.connect("marketmaker.db")
        cur = economy.cursor()

        cur.execute("""
        SELECT ID, cash
        FROM wallets
        WHERE ID NOT IN ("BANK", "TOTAL") AND cash > 1            
        """)
        rows = cur.fetchall()
        victim_row = random.choice(rows)
        bot.game_vars.victim = await bot.fetch_user(victim_row[0])
        victim_money = victim_row[1]
        economy.close()

        coin_value = random.randrange(1, math.ceil(victim_money / 4 + 1))
        announce = await channel.send(
            f"The bank's looking pretty empty, so instead, :coin: Coins :coin: from {victim}'s wallet have spawned, valued at {coin_value}$!  You can claim them by typing a word with `{bot.game_vars.seeking_substr}` within 30 seconds!",
            delete_after=30,
        )
    else:
        coin_value = random.randrange(1, math.ceil(bank_money / 6 + 10))
        if daily_counter > 0 and random.randrange(10) == 9:
            print("BONUS TIME")
            
            hard_min_words_pre = os.getenv("HARD_MIN_WORDS")
            if hard_min_words_pre is None:
                raise Exception("No HARD_MIN_WORDS provided in .env file.")

            hard_min_words = int(hard_min_words_pre)
            with open(f"{root}/static/substr_hard_{hard_min_words}.txt", "r") as f:
                hard_substrings = [line.rstrip("\n") for line in f]

            bot.game_vars.seeking_substr = random.choice(hard_substrings)
            announce = await channel.send(
                f":dollar: Bonus Coins :dollar: have spawned, valued at {coin_value + 100}$!  You can claim them by typing a word with `{bot.game_vars.seeking_substr}` within 30 seconds!",
                delete_after=30,
            )
            bonus = True
            bot.game_vars.daily_counter -= 1
        else:
            announce = await channel.send(
                f":coin: Coins :coin: from the bank have spawned, valued at {coin_value}$!  You can claim them by typing a word with `{bot.game_vars.seeking_substr}` within 30 seconds!",
                delete_after=30,
            )
            bonus = False

    def check(m):
        if not m.content:
            return False
        return (
            not m.author.bot
            and dict.check(m.content.lower())
            and bot.game_vars.seeking_substr in m.content.lower()
            and m.channel == channel
        )

    start_time = datetime.datetime.now()
    TIME_LIMIT_SEC = 30
    elapsed_time = 0.0
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
        if bot.game_vars.anarchy:
            await channel.send(
                f"Time's up!  No one claimed the :coin: Coins :coin: so {victim}'s {coin_value}$ are going to the bank!",
                delete_after=10,
            )
            await wallet_transfer(victim, "BANK", coin_value, channel, 3)
        else:
            await channel.send(
                "Time's up!  No one claimed the :coin: Coins :coin: so they've been returned to the bank...",
                delete_after=10,
            )
        bot.game_vars.seeking_substr = ""
        return

    await announce.delete()
    await msg.add_reaction("👍")
    if bot.game_vars.anarchy:
        if victim == msg.author:
            await channel.send(
                f"{msg.author} got it, so their money will be left alone.  `{msg.content.lower()}` has now been added to the list of used words.",
                delete_after=10,
            )
        else:
            await channel.send(
                f"{msg.author} got it, and {coin_value}$ has been split between the bank and their wallet, out of {victim}'s wallet!  `{msg.content.lower()}` has now been added to the list of used words.",
                delete_after=10,
            )
            await wallet_transfer(
                victim, msg.author, math.ceil(coin_value / 2), channel, 3
            )
            await wallet_transfer(victim, "BANK", math.floor(coin_value / 2), channel, 3)
    else:
        if bonus:
            await channel.send(
                f"{msg.author} got it, and {coin_value + 100}$ has been deposited into their wallet!  The economy has just grown by 100$!  `{msg.content.lower()}` has now been added to the list of used words.",
                delete_after=10,
            )
            bonus_transfer(msg.author, 100)
            bonus = False
        else:
            await channel.send(
                f"{msg.author} got it, and {coin_value}$ has been deposited into their wallet!  `{msg.content.lower()}` has now been added to the list of used words.",
                delete_after=10,
            )
        await wallet_transfer("BANK", msg.author, coin_value, channel, 2)

    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()
    cur.execute("INSERT INTO used_words VALUES (?)", (msg.content.lower(),))
    economy.commit()
    economy.close()
    bot.game_vars.seeking_substr = ""


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

    if random.randrange(100) < prob_coin and not bot.game_vars.seeking_substr and message.guild:
        await spawn_puzzle(message.channel)


@tasks.loop(time=time)
async def tax() -> None:
    print("Taxation time!")

    bot.game_vars.daily_counter = 3

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
        await wallet_transfer(user, "BANK", math.ceil(0.05 * money), channel, 6)

    bank_money = wallet_backend("BANK")

    await channel.send(
        f"Taxation time!  The value of the bank is now {bank_money}$.  Good work everyone!"
    )


@tasks.loop(seconds=random.randint(60, 600))
async def timed_puzzle() -> None:
    if not bot.game_vars.seeking_substr:
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
                    ctx.author, "BANK", int(amount), ctx.channel, 5
                )
                await ctx.send(
                    f"{ctx.author.mention}, you're only supposed to use this command with non-bots...  Don't worry, we know you want to be generous, so your {result}$ has been sent to the bank!"
                )
            else:
                result = await wallet_transfer(
                    ctx.author, receiver, int(amount), ctx.channel, 5
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
async def ledger(ctx, target: discord.User = None) -> None:
    """
    Displays a ledger of the ten most recent transactions from an individual
    """
    if target is None:
        targetid = "BANK"
        await ctx.send("No user given, showing ten most recent transactions...", delete_after = 10)
    else:
        targetid = target.id
    
    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()
    
    cur.execute("""
    SELECT time, sender, receiver, amount, type
    FROM ledger
    WHERE sender IN (?) OR receiver IN (?)
    ORDER BY time DESC
    LIMIT 10
    """,
    (targetid, targetid))
    
    rows = cur.fetchall()
    if not rows:
        await ctx.send("User has no transactions!")
        return

    ledger = ""
    transaction_dict = {
        1 : " for solving a bonus puzzle!", # bonus puzzle
        2 : " for solving a puzzle.", # puzzle
        3 : ", who was a victim of an anarchy puzzle.", # anarchy puzzle
        4 : " due to unethical behaviour.", # cheat
        5 : ", who sent it voluntarily.", # send
        6 : " as taxes", # tax
    }
    
    for row in rows:
        timestamp = row[0].split(".")[0]
        
        sendid = row[1]
        if sendid == "BANK":
            sender = "the bank"
        else:
            sender = await bot.fetch_user(int(sendid))
            
        recid = row[2]
        if recid == "BANK":
            receiver = "The bank"
        else:
            receiver = await bot.fetch_user(int(recid))
            
        amount = row[3]
        transaction = row[4]
        
        if transaction == 1:
            ledger += f"[{timestamp}] {receiver} received {amount}${transaction_dict[transaction]}\n"
        else:
            ledger += f"[{timestamp}] {receiver} received {amount}$ from {sender}{transaction_dict[transaction]}\n"

    economy.close()
    
    await ctx.send(ledger)


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
            "BANK", ctx.author, math.ceil(0.99 * bank_money), ctx.channel, 4
        )
        await ctx.send("Cheat successful!")
    else:
        result = await wallet_transfer(ctx.author, "BANK", 5, ctx.channel, 4)
        await ctx.send(
            f"{ctx.author.mention}, you have successfully donated {result}$ to the bank, good job!"
        )


# Make the bot runnable from CLI (main must be a function)
def run_bot() -> None:
    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    # this allows you to run the bot from this script too
    run_bot()
