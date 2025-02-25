import asyncio
import random
from collections import Counter
from string import ascii_uppercase

import discord
from discord.ext import commands
from nltk.corpus import wordnet as wn

import marketmaker.backend.crossword as cw


class Crossword(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        wlist = [ n for n in wn.all_lemma_names() if 3 <= len(n) <= 7 and n.isalpha() ]
        clues = [wn.synsets(word) for word in wlist]
        self.words = [cw.Word(word = word, clue = clue) for word, clue in zip(wlist, clues)]
        self.crossword = cw.CrosswordBackend(rows = 7, cols = 7, available_words = self.words)
        self.lock = asyncio.Lock()
        self.result = ""
        self.answer = ""


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
            return chr(ord(char) + 127397)  # Convert 'A' to '🇦', 'B' to '🇧', etc.
        else:
            return char


    def string_to_emojis(self, s):
        return ''.join(self.char_to_emoji(char) for char in s)


    def setup_crossword(self):
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
        print(self.crossword.current_word_list)

        self.result = f"{body}\n{guide}\nEnter your answer as the word {''.join(ascii_uppercase[:len(self.answer)])}, substituting in the letters represented by the capitals from the solved crossword."


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

