from __future__ import annotations

import sqlite3
from typing import Literal


def fetch_wallet_amount(target_id: int | Literal["BANK", "TOTAL"]) -> int:
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


def fetch_used_words() -> list[str]:
    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()

    cur.execute("SELECT word FROM used_words")
    used_word_rows = cur.fetchall()
    used_words = [row[0] for row in used_word_rows]

    economy.close()
    return used_words
