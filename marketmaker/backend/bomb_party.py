import math
import random
from pathlib import Path

import enchant

from marketmaker.backend.db import (
    bonus_transfer,
    wallet_transfer_backend,
)
from marketmaker.subclass import GameVars

enchant_dict = enchant.Dict("en_CA")

def setup_bomb(
    game_vars: GameVars,
    bonus: bool,
    normal_min_words: int,
    hard_min_words: int,
):
    root = Path(__file__).parents[2]

    if bonus:
        print("BONUS TIME")

        with open(f"{root}/static/substr_hard_{hard_min_words}.txt", "r") as f:
            hard_substrings = [line.rstrip("\n") for line in f]

        game_vars.seeking_substr = random.choice(hard_substrings)
    else:
        with open(f"{root}/static/substr_normal_{normal_min_words}.txt", "r") as f:
            normal_substrings = [line.rstrip("\n") for line in f]

        game_vars.seeking_substr = random.choice(normal_substrings)


def check_bomb(word:str, game_vars:GameVars) -> bool:
    if not word:
        return False
    return enchant_dict.check(word.lower()) and game_vars.seeking_substr in word.lower()


def finish_bomb(
    game_vars: GameVars,
    anarchy_override: bool,
    bonus: bool,
    bonus_value: int,
    msgid: int,
    coin_value: int,
) -> int:
    if game_vars.anarchy or anarchy_override:
        if game_vars.victimid != msgid:
            assert game_vars.victimid is not None
            wallet_transfer_backend(
                game_vars.victimid, msgid, math.ceil(coin_value / 2), 3
            )
            wallet_transfer_backend(
                game_vars.victimid, "BANK", math.floor(coin_value / 2), 3
            )
            outcome = 2
        else:
            outcome = 1
    else:
        if bonus:
            bonus_transfer(msgid, bonus_value)
            outcome = 3
        else:
            outcome = 4
        wallet_transfer_backend("BANK", msgid, coin_value, 2)

    return outcome
