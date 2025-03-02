import math
import random
from pathlib import Path
from string import ascii_letters
from typing import List, Literal
import yaml

from marketmaker.backend.db import bonus_transfer, wallet_transfer_backend

class HangmanBackend:
    def __init__(self):
        root = Path(__file__).parents[2]
        sign = self.read_phrase("02-significant-phrases.txt")
        prep = self.read_phrase("05-prepositional-phrases.txt")
        lit = self.read_phrase("07-literary-expressions.txt")
        sim = self.read_phrase("08-striking-similes.txt")
        conv = self.read_phrase("09-conversational-phrases.txt")
        misc = self.read_phrase("11-miscellaneous-phrases.txt")
        with (root / "static" / "phrases" / "moves.yaml").open() as f:
            moves = yaml.safe_load(f)
        self.phrase_dict = {
            "Significant phrase": sign,
            "Prepositional phrase": prep,
            "Literary expression": lit,
            "Striking simile": sim,
            "Conversational phrase": conv,
            "Miscellaneous phrase": misc,
            "Pokémon move": moves,
        }
        self.answer = ""
        self.guide = ""
        self.phrase_type = ""
        self.movedict = {}


    def begin_puzzle(self):
        self.phrase_type = random.choice(list(self.phrase_dict.keys()))
        self.answer = ""
        self.guide = ""
        if self.phrase_type == "Pokémon move":
            self.start_pokemon()
        else:
            self.start_normal()


    def start_guide(self):
        guide = []
        for word in self.answer.split():
            if len([char for char in word if char.isalpha()]) > 3:
                hword = "".join(["_" if x.isalpha() else x for x in word])
            else:
                hword = word
            guide.append(hword)
        self.guide = " ".join(guide)
        self.build_guide()


    def build_guide(self) -> str:
        blanks = self.guide.count("_")
        if blanks >= 2:
            maxhints = math.floor(blanks / 2)
            replace = list(set(random.choices(range(len(self.answer)), k = maxhints)))
            self.guide = "".join([self.answer[i] if i in replace else self.guide[i] for i in range(len(self.guide))])
        return self.guide


    def start_pokemon(self):
        pokedict = self.phrase_dict[self.phrase_type]
        pokekey = random.choice(list(pokedict.keys()))
        self.movedict = pokedict[pokekey]
        self.answer = self.movedict['name']
        print(self.answer)
        self.phrase_type = f"{self.movedict['type'].capitalize()} type, {self.movedict['category']} Pokémon move"
        self.start_guide()


    def start_normal(self):
        self.answer = random.choice(self.phrase_dict[self.phrase_type])
        print(self.answer)
        self.start_guide()


    def read_phrase(self, txtfile: str) -> List[str]:
        root = Path(__file__).parents[2]
        with open(root / "static" / "phrases" / txtfile) as f:
            return [line.rstrip("\n") for line in f if "[" not in line]

    def check(self, word: str) -> bool:
        if not word:
            return False
        return word.lower() == self.answer.lower()

    def finish(self, coin_value: int, winid: int | None = None, bonus_prize: int | None = None, vicid: int | Literal["BANK"] = "BANK"):
        if winid is None:
            if vicid != "BANK":
                wallet_transfer_backend(sendid = vicid, recid = "BANK", amount = coin_value, transaction = 3)
        elif vicid != "BANK":
            wallet_transfer_backend(
                vicid, winid, math.ceil(coin_value / 2), 3
            )
            wallet_transfer_backend(
                vicid, "BANK", math.floor(coin_value / 2), 3
            )
        elif winid != vicid:
            wallet_transfer_backend(sendid = "BANK", recid = winid, amount = coin_value, transaction = 2)

        if bonus_prize is not None and winid is not None and bonus_prize != 0:
            bonus_transfer(winid, bonus_prize)
