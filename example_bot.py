# This example requires the 'message_content' intent.

import discord
import os
import sqlite3
import random
import asyncio
import math
from collections import defaultdict
from discord.ext import commands

import enchant
dict = enchant.Dict("en_CA")

from nltk.corpus import words
word_list = words.words()

from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

prob_coin = 2
total_money = 100000
bank_money = total_money
coin_value = random.randrange(1, math.ceil(bank_money/6 + 10))
with open("substr_250.txt", 'r') as f:
    good_substrings = [line.rstrip('\n') for line in f]
seeking_substr = ""
victim = ""
anarchy = False

used_words = []
wallets = defaultdict(int)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='##', intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    print(bot.guilds)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    await bot.process_commands(message)

    global seeking_substr
    global used_words
    global wallets
    global victim
    global anarchy
    global bank_money
    global total_money
    
    if random.randrange(100) < prob_coin and not seeking_substr and message.guild:   
        if anarchy:
            anarchy = bank_money > total_money/5
        else:
            anarchy = bank_money < total_money/90
        
        seeking_substr = random.choice(good_substrings)
        if anarchy:
            victim = random.choice([key for key, value in wallets.items() if value > 1])
            coin_value = random.randrange(1, math.ceil(wallets[victim]/4 + 1))
            announce = await message.channel.send(f"The bank's looking pretty empty, so instead, :coin: Coins :coin: from {victim.mention}'s wallet have spawned, valued at {coin_value}$!  You can claim them by typing a word with `{seeking_substr}` within 30 seconds!", delete_after = 30)
        else:
            coin_value = random.randrange(1, math.ceil(bank_money/6 + 10))
            announce = await message.channel.send(f":coin: Coins :coin: from the bank have spawned, valued at {coin_value}$!  You can claim them by typing a word with `{seeking_substr}` within 30 seconds!", delete_after = 30)
        
        def check(m):
            if m.content in used_words:
                m.add_reaction("❌")
            return not m.author.bot and dict.check(str.lower(m.content)) and seeking_substr in m.content and m.channel == message.channel and not m.content in used_words
        
        try:
            msg = await bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            if anarchy:
                await message.channel.send(f"Time's up!  No one claimed the :coin: Coins :coin: so {victim.mention}'s {coin_value}$ are going to the bank!", delete_after = 10)
                bank_money += coin_value
                wallets[victim] -= coin_value
            else:
                await message.channel.send("Time's up!  No one claimed the :coin: Coins :coin: so it has been returned to the bank...", delete_after = 10)
            seeking_substr = ""
            return
        
        await msg.add_reaction("👍")
        await announce.delete()
        if anarchy:
            await message.channel.send(f"{msg.author.mention} got it, and {coin_value}$ has been split between the bank and their wallet, out of {victim.mention}'s wallet!  `{msg.content}` has now been added to the list of used words.", delete_after = 10)
            wallets[msg.author] += math.ceil(coin_value/2)
            wallets[msg.author] += math.floor(coin_value/2)
            wallets[victim] -= coin_value
        else:
            await message.channel.send(f"{msg.author.mention} got it, and {coin_value}$ has been deposited into their wallet!  `{msg.content}` has now been added to the list of used words.", delete_after = 10)
            wallets[msg.author] += coin_value
            bank_money -= coin_value
        used_words.append(msg.content)
        seeking_substr = ""
        
@bot.hybrid_command()
async def wallet(ctx):
    global wallets
    await ctx.send(f"{ctx.author.mention} has {wallets[ctx.author]}$ in their wallet!")

@bot.hybrid_command()
async def used(ctx):
    global used_words
    await ctx.send(f"{used_words}")
    
@bot.hybrid_command()
async def bank(ctx):
    global bank_money
    global total_money
    await ctx.send(f"The bank currently has {bank_money}$, out of a total of {total_money}$ in the economy!")

# @bot.hybrid_command()
# async def cheat(ctx):
#     global bank_money
#     global wallets
#     wallets[ctx.author] += math.ceil(0.99*bank_money)
#     bank_money -= math.ceil(0.99*bank_money)
#     await ctx.send("Cheat successful!")

bot.run(BOT_TOKEN)