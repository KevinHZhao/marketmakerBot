from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from marketmaker.backend.bomb_party import setup_bomb

if TYPE_CHECKING:
    from marketmaker.subclass import MarketmakerBot


def test_setup_bomb(bot: MarketmakerBot, event_loop):
    # Simple test for bomb_party, will add more in the future
    root = Path(__file__).parents[1]

    with open(f"{root}/static/substr_normal_{bot.normal_min_words}.txt") as f:
        normal_substrings = [line.rstrip("\n") for line in f]

    with open(f"{root}/static/substr_hard_{bot.hard_min_words}.txt") as f:
        hard_substrings = [line.rstrip("\n") for line in f]

    test1_result = setup_bomb(bot.game_vars, True, bot.normal_min_words, bot.hard_min_words, 123, False, None)
    assert test1_result == (123, 3)
    assert bot.game_vars.seeking_substr in hard_substrings
    assert bot.game_vars.daily_counter == 2
