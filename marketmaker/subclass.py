from dataclasses import dataclass

from discord.ext import commands
from typing import Optional
from marketmaker.configs import (
    prob_coin,
    BOT_TOKEN,
    normal_min_words,
    hard_min_words,
    timed,
    channelid,
    dev
)

@dataclass
class GameVars:
    seeking_substr: str = ""
    victimid: Optional[int] = None
    anarchy: bool = False
    daily_counter: int = 3
    
    
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