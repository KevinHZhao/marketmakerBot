import asyncio
import random
from collections import Counter
from string import ascii_uppercase

import discord
from discord.ext import commands
from nltk.corpus import wordnet as wn

import marketmaker.backend.crossword as cw
from marketmaker.backend.db import fetch_used_words


class Crossword(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.wlist: list = []
        self.clues: list = []
        self.words: list = []
        self.lock = asyncio.Lock()
        self.result = ""
        self.answer = ""
        self.emojidict: dict = {}
        self.crossword = cw.CrosswordBackend(rows = 7, cols = 7, available_words = [cw.Word(word = "ERROR", clue = wn.synsets("error"))])
        self.reset_emoji_dict()
        self.refresh_words()


    def refresh_words(self):
        raw_wlist = list(set([wn.synsets(x)[0].name().split(".", 1)[0] for x in fetch_used_words() if wn.synsets(x)]))
        self.wlist = [x for x in raw_wlist if 2 <= len(x) <= 7]
        self.clues = [wn.synsets(word) for word in self.wlist]
        self.words = [cw.Word(word = word, clue = clue) for word, clue in zip(self.wlist, self.clues)]
        self.crossword.available_words = self.words


    def reset_emoji_dict(self):
        emoji_symbols = [
            '🔅', '🔆', '📳', '📴', '🔋', '💡',
            '🕯️', '🛢️', '💸', '💵', '💴', '💶', '💷', '💰', '💳', '💎', '⚖️',
            '🗜️', '⚗️', '🔬', '🔭', '📡', '💉', '💊', '🚪', '🛏️', '🛋️', '🚽', '🚿', '🛁',
            '🚬', '⚰️', '⚱️', '🗿', '🛎️', '🧳', '⌛', '⏳', '⌚', '⏰', '⏱️', '⏲️', '🕰️', '🌡️', '⛱️',
            '🧯', '🧰', '🧲', '🧪', '🧫', '🧬', '🧴', '🧹', '🧺', '🧻', '🧼', '🧽', '🧯'
        ]
        random.shuffle(emoji_symbols)
        self.emojidict = {letter: emoji for letter, emoji in zip(ascii_uppercase, emoji_symbols)}


    def is_crossword_running(self) -> bool:
        return self.lock.locked()


    def can_form_word(self, word, char_list):
        # Count the frequency of characters in the word
        word_count = Counter(word)
        # Count the frequency of characters in the char_list
        char_count = Counter(char_list)

        # Check if the word can be formed using the characters in char_list
        return all(char_count[char] >= count for char, count in word_count.items())

    def filter_words(self, words, char_list):
        return [word for word in words if self.can_form_word(word, char_list)]


    def char_to_emoji(self, char):
        if char == '_':
            return '⬛'
        elif char == ' ':
            return '⏹️'
        elif char == '\n':
            return '\n'  # Preserve newlines, just in case
        elif char.isdigit():
            return f'{char}️⃣'
        elif char.isupper():
            return self.emojidict[char]  # Convert 'A' to '🇦', 'B' to '🇧', etc.
        else:
            return char


    def string_to_emojis(self, s):
        return ''.join(self.char_to_emoji(char) for char in s)


    def setup_crossword(self):
        self.refresh_words()
        self.reset_emoji_dict()
        self.crossword.current_word_list = []
        self.crossword.clear_grid()
        self.crossword.randomize_word_list()
        self.crossword.compute_crossword()
        self.crossword.display() # This replaces the first letters with numbers so they can't be subbed out
        avail = Counter([x for xs in self.crossword.grid for x in xs if str(x).isalpha()])
        filtered_words = self.filter_words([x.word for x in self.words], avail)
        self.answer = random.choice(filtered_words)
        body = self.string_to_emojis(self.crossword.replace_letters_in_solution(self.answer))
        guide = self.crossword.legend()

        print(repr(body))
        print(self.crossword.display())
        print(self.crossword.solution())
        print(guide)
        print(self.crossword.current_word_list)

        self.result = f"{body}\n```{guide}```\nEnter your answer as the word {''.join([self.emojidict[x] for x in list(ascii_uppercase[:len(self.answer)])])}, substituting in the letters represented by the symbols from the solved crossword."
        print(self.result)


    async def view_crossword(self, channel: discord.TextChannel) -> None:
        if not self.crossword.current_word_list and not self.lock.locked():
            self.setup_crossword()
        if not self.crossword.current_word_list and self.lock.locked():
            await channel.send("Currently generating a crossword, please check back in a minute...")
            return

        await channel.send(self.result)


    async def check_crossword(self, channel: discord.TextChannel, propans: str) -> None:
        if propans.lower() == self.answer.lower():
            self.crossword.current_word_list = []
            self.answer = ""
            await channel.send("Correct!  You get nothing since this is still in development")
            self.setup_crossword()
        else:
            await channel.send("Incorect!")

