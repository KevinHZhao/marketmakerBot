from dataclasses import dataclass

import discord
from discord.ext import commands
from typing import Optional


@dataclass
class GameVars:
    seeking_substr: str = ""
    victim: Optional[discord.User] = None
    anarchy: bool = False
    daily_counter: int = 3
    
    
class MarketmakerBot(commands.Bot):
    game_vars = GameVars()
    
# def __init__(self):
#     super().__init__()
#     self.game_vars = GameVars()