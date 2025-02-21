import math
import random
from pathlib import Path
from typing import Optional

import discord
import enchant

from marketmaker.backend.db import (
    bonus_transfer,
    fetch_wallet_amount,
    generate_victim,
    wallet_transfer_backend,
)
from marketmaker.subclass import GameVars

enchant_dict = enchant.Dict("en_CA")

def setup_bomb(
    game_vars: GameVars,
    bonus: bool,
    normal_min_words: int,
    hard_min_words: int,
    coin_value: Optional[int] = None,
    anarchy_override: bool = False,
    anarchy_victim: discord.Member = None,
) -> tuple[int, int]:
    bank_money = fetch_wallet_amount("BANK")

    root = Path(__file__).parents[2]

    with open(f"{root}/static/substr_normal_{normal_min_words}.txt", "r") as f:
        normal_substrings = [line.rstrip("\n") for line in f]

    game_vars.seeking_substr = random.choice(normal_substrings)

    if anarchy_override:
        game_vars.victimid = anarchy_victim.id
        coin_value = fetch_wallet_amount(anarchy_victim.id)
        outcome = 1
    elif game_vars.anarchy:
        game_vars.victimid, victim_money = generate_victim()
        game_vars.victimid = int(game_vars.victimid)
        coin_value = random.randrange(1, math.ceil(victim_money / 4 + 1))
        outcome = 2
    else:
        if coin_value is None:
            coin_value = random.randrange(1, math.ceil(bank_money / 6 + 10))
        if bonus:
            print("BONUS TIME")

            with open(f"{root}/static/substr_hard_{hard_min_words}.txt", "r") as f:
                hard_substrings = [line.rstrip("\n") for line in f]

            game_vars.seeking_substr = random.choice(hard_substrings)
            game_vars.daily_counter -= 1
            outcome = 3
        else:
            outcome = 4

    return (coin_value, outcome)


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
