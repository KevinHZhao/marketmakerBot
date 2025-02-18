from __future__ import annotations

import asyncio
import datetime
import math
import os
import random
import sqlite3
from pathlib import Path
from typing import Literal, Union, Optional

import discord
import enchant
from discord.ext import tasks
from dotenv import load_dotenv
from pytz import timezone
from functools import partial

from marketmaker.backend import used_words_backend, wallet_backend
from marketmaker.initialization import ensure_db, ensure_substr
from marketmaker.subclass import MarketmakerBot

dict = enchant.Dict("en_CA")

load_dotenv()

# Setup
prob_coin_env = os.getenv("PROB")
if prob_coin_env is None:
    raise Exception("No PROB provided in .env file.")
prob_coin = int(prob_coin_env)

dev_mode_env = os.getenv("DEV_MODE")
if dev_mode_env is None:
    raise Exception("No DEV_MODE provided in .env file.")
dev = bool(int(dev_mode_env))

# Game data init
ensure_substr()
ensure_db()

time = datetime.time(hour=5, minute=0, tzinfo=datetime.UTC)

intents = discord.Intents.default()
intents.message_content = True

bot = MarketmakerBot(command_prefix="##", intents=intents)


def bonus_transfer(receiver: Union[discord.User, Literal["BANK"]], amount: int, transaction: int = 1) -> None:
    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()

    if isinstance(receiver, (discord.User, discord.Member)):
        recid: Union[Literal["BANK"], int] = receiver.id
    elif receiver != "BANK":
        raise Exception("receiver is neither discord.User nor BANK!")
    else:
        recid = "BANK"

    receiver_cash = wallet_backend(recid)
    total_cash = wallet_backend("TOTAL")

    cur.execute(
        "UPDATE wallets SET cash = ? WHERE ID = ?", (receiver_cash + amount, recid)
    )
    cur.execute(
        "UPDATE wallets SET cash = ? WHERE ID = ?", (total_cash + amount, "TOTAL")
    )
    
    timestamp = datetime.datetime.now(timezone("US/Eastern"))
    
    cur.execute(
        "INSERT INTO ledger (time, sender, receiver, amount, type) VALUES (?, 'N/A', ?, ?, ?)",
        (timestamp, recid, amount, transaction)
    )

    economy.commit()
    economy.close()
    print(f"Gave {amount} to {receiver} as a bonus.")
    
    
async def force_anarchy(channel: discord.TextChannel):
    await channel.send("Anarchy has been forcibly activated!")
    bot.game_vars.anarchy = True


async def force_deflation(channel: discord.TextChannel, user: discord.User, amount: int):
    user_cash = wallet_backend(user.id)
    if user_cash < amount:
        raise Exception(f"Something went wrong, amount {amount} is not less than user_cash {user_cash}.")
    await channel.send(f"Deflation!  {amount}$ of {user.mention}'s cash has been lost!  The economy shrinks by {amount}$.")
    bonus_transfer(user, -amount, 9)
    
    
async def force_inflation(channel: discord.TextChannel, user: discord.User, amount: int):
    await channel.send(f"Bonus inflation!  {amount}$ has appeared from out of nowhere into {user.mention}'s wallet!  The economy grows by {amount}$.")
    bonus_transfer(user, amount, 8)


async def donation(channel:discord.TextChannel, sender: discord.User, receiver: Union[discord.User, Literal["BANK"]], amount: int):
    if receiver == "BANK":
        await channel.send(f"{sender.mention} must be feeling generous, since they just donated a further {amount}$ to the bank on top of their initial wager!")
    else:
        await channel.send(f"{sender.mention} must be feeling generous, since they just donated {amount}$ to {receiver.mention}!")
    
    await wallet_transfer(sender, receiver, amount, channel, 5)


async def wallet_transfer(
    sender: Union[discord.User, Literal["BANK"]],
    receiver: Union[discord.User, Literal["BANK"]],
    amount: int,
    channel: discord.TextChannel,
    transaction: int
) -> int:
    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()

    if isinstance(receiver, (discord.User, discord.Member)):
        recid: Union[Literal["BANK"], int] = receiver.id
    elif receiver != "BANK":
        raise Exception("receiver is neither discord.User nor BANK")
    else:
        recid = "BANK"
        
    if isinstance(sender, (discord.User, discord.Member)):
        sendid: Union[Literal["BANK"], int] = sender.id
    elif sender != "BANK":
        raise Exception("sender is neither discord.User nor BANK")
    else:
        sendid = "BANK"

    sender_cash = wallet_backend(sendid)

    if sender_cash < amount:
        if isinstance(sender, (discord.User, discord.Member)):
            sendmen = sender.mention
        elif sender != "BANK":
            raise Exception("sender is neither discord.User nor BANK")
        else:
            sendmen = "The bank"

        if isinstance(receiver, (discord.User, discord.Member)):
            recmen = receiver.mention
        elif receiver != "BANK":
            raise Exception("receiver is neither discord.User nor BANK")
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
    
    timestamp = datetime.datetime.now(timezone("US/Eastern"))
    
    cur.execute(
        "INSERT INTO ledger (time, sender, receiver, amount, type) VALUES (?, ?, ?, ?, ?)",
        (timestamp, sendid, recid, amount, transaction)
    )

    economy.commit()
    economy.close()
    print(f"Transferred {result} from {sender} to {receiver}.")
    return result


async def spawn_puzzle(channel: discord.TextChannel, coin_value: Optional[int] = None, bonus_value: int = 100, anarchy_override: bool = False, anarchy_victim: Optional[discord.User] = None) -> None:
    bank_money = wallet_backend("BANK")
    total_money = wallet_backend("TOTAL")
    used_words = used_words_backend()

    if bot.game_vars.anarchy:
        bot.game_vars.anarchy = bank_money < total_money / 5
    else:
        bot.game_vars.anarchy = bank_money < total_money / 90

    root = Path(__file__).parents[1]
    
    normal_min_env = os.getenv("NORMAL_MIN_WORDS")
    if normal_min_env is None:
        raise Exception("No NORMAL_MIN_WORDS provided in .env file.")
    normal_min_words = int(normal_min_env)

    with open(f"{root}/static/substr_normal_{normal_min_words}.txt", "r") as f:
        normal_substrings = [line.rstrip("\n") for line in f]

    bot.game_vars.seeking_substr = random.choice(normal_substrings)
    
    if anarchy_override:
        assert anarchy_victim is not None
        victim_money = wallet_backend(anarchy_victim.id)
        if victim_money == 0:
            await channel.send(f"We were going to put all of {anarchy_victim.mention}'s money up for a puzzle, but they don't have any left!  Nothing happens...", delete_after=20)
            return
        bot.game_vars.victim = anarchy_victim
        coin_value = victim_money
        
        announce = await channel.send(
            f"{bot.game_vars.victim.mention}, all {coin_value}$ from your wallet has spawned, unlucky!  Anyone can claim them by typing a word with `{bot.game_vars.seeking_substr}` within 30 seconds!",
            delete_after=30,
        )
    elif bot.game_vars.anarchy:
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
            f"The bank's looking pretty empty, so instead, :coin: Coins :coin: from {bot.game_vars.victim}'s wallet have spawned, valued at {coin_value}$!  You can claim them by typing a word with `{bot.game_vars.seeking_substr}` within 30 seconds!",
            delete_after=30,
        )
    else:
        if coin_value is None:
            coin_value = random.randrange(1, math.ceil(bank_money / 6 + 10))
        if bot.game_vars.daily_counter > 0 and random.randrange(10) == 9:
            print("BONUS TIME")
            
            hard_min_words_env = os.getenv("HARD_MIN_WORDS")
            if hard_min_words_env is None:
                raise Exception("No HARD_MIN_WORDS provided in .env file.")
            hard_min_words = int(hard_min_words_env)
            
            with open(f"{root}/static/substr_hard_{hard_min_words}.txt", "r") as f:
                hard_substrings = [line.rstrip("\n") for line in f]

            bot.game_vars.seeking_substr = random.choice(hard_substrings)
            announce = await channel.send(
                f":dollar: Bonus Coins :dollar: have spawned, valued at {coin_value + bonus_value}$!  You can claim them by typing a word with `{bot.game_vars.seeking_substr}` within 30 seconds!",
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
                f"Time's up!  No one claimed the :coin: Coins :coin: so {bot.game_vars.victim}'s {coin_value}$ are going to the bank!",
                delete_after=10,
            )
            assert bot.game_vars.victim is not None
            assert isinstance(coin_value, int)
            await wallet_transfer(bot.game_vars.victim, "BANK", coin_value, channel, 3)
        else:
            await channel.send(
                "Time's up!  No one claimed the :coin: Coins :coin: so they've been returned to the bank...",
                delete_after=10,
            )
        bot.game_vars.seeking_substr = ""
        return

    await announce.delete()
    await msg.add_reaction("👍")
    if bot.game_vars.anarchy or anarchy_override:
        if bot.game_vars.victim == msg.author:
            await channel.send(
                f"{msg.author} got it, so their money will be left alone.  `{msg.content.lower()}` has now been added to the list of used words.",
                delete_after=10,
            )
        else:
            await channel.send(
                f"{msg.author} got it, and {coin_value}$ has been split between the bank and their wallet, out of {bot.game_vars.victim}'s wallet!  `{msg.content.lower()}` has now been added to the list of used words.",
                delete_after=10,
            )
            
            assert bot.game_vars.victim is not None
            await wallet_transfer(
                bot.game_vars.victim, msg.author, math.ceil(coin_value / 2), channel, 3
            )
            await wallet_transfer(bot.game_vars.victim, "BANK", math.floor(coin_value / 2), channel, 3)
    else:
        if bonus:
            await channel.send(
                f"{msg.author} got it, and {coin_value + bonus_value}$ has been deposited into their wallet!  The economy has just grown by {bonus_value}$!  `{msg.content.lower()}` has now been added to the list of used words.",
                delete_after=10,
            )
            bonus_transfer(msg.author, bonus_value)
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
    
    time_env = os.getenv("TIMED_SPAWN")
    if time_env is None:
        raise Exception("No TIMED_SPAWN provided in .env file.")
    timed = bool(int(time_env))
    
    if timed:
        timed_puzzle.start()
    tax.start()
    await bot.tree.sync()


@bot.event
async def on_message(message) -> None:
    if message.author.bot:
        return

    await bot.process_commands(message)

    if random.randrange(100) < prob_coin and bot.game_vars.seeking_substr == "" and message.guild:
        await spawn_puzzle(message.channel)


@tasks.loop(time=time)
async def tax() -> None:
    print("Taxation time!")

    bot.game_vars.daily_counter = 3
    
    channel_env = os.getenv("CHANNEL")
    if channel_env is None:
        raise Exception("No CHANNEL provided in .env file.")
    channel = await bot.fetch_channel(int(channel_env))
        
    if not isinstance(channel, discord.TextChannel):
        raise Exception("Provided CHANNEL points to a non-text channel.")

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
    if bot.game_vars.seeking_substr == "":
        channel_env = os.getenv("CHANNEL")
        if channel_env is None:
            raise Exception("No CHANNEL provided in .env file.")
        channel = await bot.fetch_channel(int(channel_env))
        
        if not isinstance(channel, discord.TextChannel):
            raise Exception("Provided CHANNEL points to a non-text channel.")
        
        await spawn_puzzle(channel)


@bot.hybrid_command(name="wallet")
async def cmd_wallet(ctx, target: Optional[discord.User] = None) -> None:
    """
    Displays a selected user's wallet.  Defaults to command user.
    """
    if target is None:
        target = ctx.author
    money = wallet_backend(target.id)
    await ctx.send(f"{target} has {money}$ in their wallet!")


@bot.hybrid_command(name="used")
async def cmd_used(ctx) -> None:
    """
    Displays all previously used words in the game.
    """
    used_words = used_words_backend()

    words_string = ""
    for word in used_words:
        words_string += "`" + word + "`, "
    words_string = words_string[:-2] + "."
    await ctx.send(words_string)


@bot.hybrid_command(name="bank")
async def cmd_bank(ctx) -> None:
    """
    Displays the current money in the bank and the total money in the economy.
    """
    bank_money = wallet_backend("BANK")
    total_money = wallet_backend("TOTAL")
    await ctx.send(
        f"The bank currently has {bank_money}$, out of a total of {total_money}$ in the economy!"
    )


@bot.hybrid_command(name="send")
async def cmd_send(ctx, receiver: discord.User, amount: int) -> None:
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


@bot.hybrid_command(name="leaderboard")
async def cmd_leaderboard(ctx) -> None:
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
    

@bot.hybrid_command(name="ledger")
async def cmd_ledger(ctx, target: Optional[discord.User]) -> None:
    """
    Displays a ledger of the ten most recent transactions from an individual
    """
    if isinstance(target, (discord.User, discord.Member)):
        targetid: Union[Literal["BANK"], int] = target.id
    elif target is not None:
        raise Exception("target is neither discord.User nor None!")
    else:
        targetid = "BANK"
        await ctx.send("No user given, showing ten most recent transactions...", delete_after = 10)
    
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
        5 : " as a donation.", # send/donate
        6 : " as taxes.", # tax
        7 : " as a wager.", # random
        8 : " as a bonus.", # force_inflation
        9 : " due to deflation." # force_deflataion
    }
    
    for row in rows:
        timestamp = row[0].split(".")[0]
        
        sendid = row[1]
        if sendid == "BANK":
            sender: Union[Literal["the bank"], discord.User, None] = "the bank"
        elif sendid == "N/A":
            sender = None
        else:
            sender = await bot.fetch_user(int(sendid))
            
        recid = row[2]
        if recid == "BANK":
            receiver: Union[Literal["The bank"], discord.User] = "The bank"
        else:
            receiver = await bot.fetch_user(int(recid))
            
        amount = row[3]
        transaction = row[4]
        
        if transaction in [1, 8]:
            ledger += f"[{timestamp}] {receiver} received {amount}${transaction_dict[transaction]}\n"
        elif transaction == 9:
            ledger += f"[{timestamp}] {receiver} lost {amount}${transaction_dict[transaction]}\n"
        else:
            ledger += f"[{timestamp}] {receiver} received {amount}$ from {sender}{transaction_dict[transaction]}\n"

    economy.close()
    
    await ctx.send(ledger)


@bot.hybrid_command(name="random")
async def cmd_random_event(ctx, wager: Optional[int] = None) -> None:
    """
    Causes a random event to occur, requires a wager rom the user.
    """
    if wager <= 0:
        await ctx.send(f"{ctx.author.mention}, you must provide a positive integer wager!")
        return
    
    if bot.game_vars.seeking_substr != "":
        await ctx.send(f"{ctx.author.mention}, wait for the current puzzle to end before using this command!")
        return
    
    user_money = wallet_backend(ctx.author.id)
    assert isinstance(wager, int)
    if wager > user_money:
        await ctx.send(f"{ctx.author.mention}, you don't have enough money for that wager!")
        return
    
    await wallet_transfer(ctx.author, "BANK", wager, ctx.channel, 7)
    
    await ctx.send(f"{ctx.author.mention}, your wager of {wager}$ has been accepted by the bank.  Now rolling the dice...")
    bank_money = wallet_backend("BANK")
    all_puzzle = partial(spawn_puzzle, channel = ctx.channel, anarchy_override = True, anarchy_victim = ctx.author)
    normal_puzzle = partial(spawn_puzzle, channel = ctx.channel)
    
    buffed_value = min(math.ceil(wager*1.5), bank_money - 1)
    buffed_puzzle = partial(spawn_puzzle, channel = ctx.channel, coin_value = buffed_value, bonus_value = 500)
    
    bonus = min(math.ceil(wager/2), user_money)
    deflation = partial(force_deflation, channel = ctx.channel, user = ctx.author, amount = bonus)
    inflation = partial(force_inflation, channel = ctx.channel, user = ctx.author, amount = bonus)
    bank_donation = partial(donation, channel = ctx.channel, sender = ctx.author, receiver = "BANK", amount = bonus)
    
    anarchy = partial(force_anarchy, channel = ctx.channel)
    
    funcs = [all_puzzle, normal_puzzle, buffed_puzzle, anarchy, deflation, inflation, bank_donation, tax]
    
    # Create weights for funcs depending on wager
    if wager < 100:
        weights = (0.05, 0.4, 0.02, 0.03, 0.025, 0.025, 0.4, 0.05)
    elif 100 <= wager < 250:
        weights = (0.04, 0.25, 0.3, 0.05, 0.04, 0.04, 0.23, 0.05)
    elif 250 <= wager < 500:
        weights = (0.03, 0.15, 0.4, 0.07, 0.08, 0.08, 0.16, 0.03)
    elif 500 <= wager < 1000:
        weights = (0.02, 0.1, 0.5, 0.07, 0.08, 0.08, 0.13, 0.02)
    else:
        weights = (0.01, 0, 0.6, 0.13, 0.13, 0.13, 0, 0)
    
    selected_fun = random.choices(
        funcs,
        weights = weights,
        k = 1
    )[0]
    
    await selected_fun()
    


@bot.hybrid_command(name="force_tax")
async def cmd_force_tax(ctx) -> None:
    """
    Developer command, forces taxation on all users.
    """
    if dev:
        await tax()
    else:
        await ctx.send("No.")


@bot.hybrid_command(name="cheat")
async def cmd_cheat(ctx) -> None:
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
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if BOT_TOKEN is None:
        raise Exception("No BOT_TOKEN provided in .env file.")
    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    # this allows you to run the bot from this script too
    run_bot()
