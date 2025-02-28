from dataclasses import dataclass
from typing import Optional

from discord.ext import commands

from marketmaker.configs import (
    BOT_TOKEN,
    channelid,
    dev,
    hard_min_words,
    normal_min_words,
    prob_coin,
    timed,
)


@dataclass
class GameVars:
    seeking_substr: str = ""
    victimid: Optional[int] = None
    anarchy: bool = False


class MarketmakerBot(commands.Bot):
    game_vars = GameVars()
    prob_coin = prob_coin
    BOT_TOKEN = BOT_TOKEN
    normal_min_words = normal_min_words
    hard_min_words = hard_min_words
    timed = timed
    channelid = channelid
    dev = dev


# def __init__(self):
#     super().__init__()
#     self.game_vars = GameVars()