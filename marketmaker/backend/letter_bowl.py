import math
import random
from string import ascii_lowercase
from typing import List, Literal

import enchant

from marketmaker.backend.db import bonus_transfer, wallet_transfer_backend

enchant_dict = enchant.Dict("en_CA")

class LetterBowlBackend:
    def __init__(self):
        self.letters = []
        self.wordcount = 0
        self.minwlen = 1
        self.restart()


    def restart(self):
        vow1 = "aeo" ## "More" common vowels
        vow2 = "iu" ## "Less" common vowels
        cons1 = "thnsr" ## Cons above 5%
        cons2 = "dlwcm" ## Cons above 2.5%
        cons3 = "bfgpvy" ## Cons above 1%
        cons4 = "jkqxz" ## Cons below 1%
        templet = [random.choice(vow1), random.choice(vow2), random.choice(cons1), random.choice(cons2), random.sample(cons3, 2), random.sample(cons4, 3)]
        templet = [j for i in templet for j in i]
        self.letters = sorted(list(set(templet + random.sample(ascii_lowercase, 4))))
        self.wordcount = 0
        self.minwlen = 1


    def check_word(self, word:str) -> bool:
        return bool(len(word) >= self.minwlen and enchant_dict.check(word.lower()) and all(let in self.letters for let in word.lower()))


    def increment(self, word:str):
        self.wordcount += 1
        self.minwlen = len(word) + 1


    def start(self) -> list[str]:
        self.restart()
        return self.letters


    def finish(self, prize: int, winid: int | None = None, base_bonus: int = 0, vicid: int | Literal["BANK"] = "BANK") -> List[int]:
        score = self.wordcount
        if winid is None:
            if vicid != "BANK":
                wallet_transfer_backend(sendid = vicid, recid = "BANK", amount = prize, transaction = 3)
        else:
            to_winner = max(math.ceil(prize * score / 7), prize)
            if winid == vicid:
                to_winner = 0
            elif vicid != "BANK":
                to_winner = min(to_winner, math.ceil(prize * 3 / 4))
                wallet_transfer_backend(sendid = vicid, recid = "BANK", amount = prize - to_winner, transaction = 3)
                wallet_transfer_backend(sendid = vicid, recid = winid, amount = to_winner, transaction = 3)
            else:
                wallet_transfer_backend(sendid = "BANK", recid = winid, amount = to_winner, transaction = 2)

        bonus_prize = base_bonus * score
        if base_bonus and winid is not None:
            bonus_transfer(winid, base_bonus * score)
        self.restart()
        return [score, to_winner, bonus_prize]
