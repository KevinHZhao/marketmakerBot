from __future__ import annotations

import sqlite3
import discord
from typing import Literal
from pathlib import Path

DB_PATH = Path("marketmaker.db")  # relative to executable


def wallet_backend(target_id: int | Literal["BANK", "TOTAL"]) -> int:
    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()

    cur.execute("SELECT 1 FROM wallets WHERE ID = ?", (target_id,))
    if cur.fetchone() is None:
        print(f"{target_id} wallet created!")
        cur.execute("INSERT INTO wallets (ID, cash) VALUES (?, 0)", (target_id,))
        economy.commit()

    cur.execute("SELECT cash FROM wallets WHERE ID = ?", (target_id,))
    money = cur.fetchone()[0]

    economy.close()
    return money


def used_words_backend() -> list[str]:
    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()

    cur.execute("SELECT word FROM used_words")
    used_word_rows = cur.fetchall()
    used_words = [row[0] for row in used_word_rows]

    economy.close()
    return used_words


def timer_board_add(userid: int, sol_time: float, word: str, substr: str) -> None:
    """
    Checks if a user's puzzle solution should be added as their personal best on the timerboard.
    """
    economy = sqlite3.connect(DB_PATH)
    cur = economy.cursor()
    
    cur.execute("CREATE TABLE IF NOT EXISTS timeboard(ID INTEGER PRIMARY KEY, time REAL, word TEXT, substr TEXT)")
    
    cur.execute("SELECT 1 FROM timeboard WHERE ID = ?", (userid,))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO timeboard (ID, time, word, substr) VALUES (?, ?, ?, ?)", (userid, sol_time, word, substr))
        economy.commit()
        economy.close()
        return

    cur.execute("SELECT time FROM timeboard WHERE ID = ?", (userid,))
    prev_time = cur.fetchone()[0]
    if sol_time < prev_time:
        cur.execute("INSERT INTO timeboard (ID, time, word, substr) VALUES (?, ?, ?, ?)", (userid, sol_time, word, substr))
    
    economy.commit()
    economy.close()
    

async def reset_timer_board(channel: discord.TextChannel) -> None:
    economy = sqlite3.connect(DB_PATH)
    cur = economy.cursor()
    
    cur.execute("DROP TABLE IF EXISTS timeboard")
    cur.execute("CREATE TABLE timeboard(ID INTEGER PRIMARY KEY, time REAL, word TEXT, substr TEXT)")

    await channel.send(
        f"The time trial leaderboard has been reset!"
    )
    
    economy.commit()
    economy.close()