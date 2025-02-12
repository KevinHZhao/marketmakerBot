# This example requires the 'message_content' intent.

import discord
import os
import sqlite3
import random
import asyncio
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
coin_value = 1000
with open("substr_250.txt", 'r') as f:
    good_substrings = [line.rstrip('\n') for line in f]
seeking_substr = ""

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
    
    if random.randrange(100) < prob_coin and not seeking_substr:        
        seeking_substr = random.choice(good_substrings)
        announce = await message.channel.send(f":coin: Coins :coin: have spawned, valued at {coin_value}$!  You can claim them by typing a word with `{seeking_substr}` within 30 seconds!", delete_after = 30)
        
        def check(m):
            return not m.author.bot and dict.check(m.content) and seeking_substr in m.content and m.channel == message.channel and not m.content in used_words
        
        try:
            msg = await bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            await message.channel.send("Time's up!  No one claimed the :coin: Coins :coin: so it has been returned to the bank...", delete_after = 10)
            seeking_substr = ""
            return
        
        await msg.add_reaction("👍")
        await announce.delete()
        await message.channel.send(f"{msg.author.mention} got it, and {coin_value}$ has been deposited into their wallet!  `{msg.content}` has now been added to the list of used words.", delete_after = 10)
        wallets[msg.author] += coin_value
        used_words.append(msg.content)
        seeking_substr = ""
    
    print(used_words)
    print(wallets)
        
@bot.hybrid_command()
async def wallet(ctx):
    global wallets
    await ctx.send(f"{ctx.author.mention} has {wallets[ctx.author]}$ in their wallet!")

bot.run(BOT_TOKEN)