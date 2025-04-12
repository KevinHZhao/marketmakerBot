from __future__ import annotations

import math
import random
import sqlite3
from pytz import timezone
from datetime import datetime, timedelta

from marketmaker.backend.db import (
    bonus_transfer,
    fetch_wallet_amount,
)


def create_futures(
    user_id: int,
    channel_id: int,
    duration: timedelta,
    bet: int,
    target_growth: int,
    ):
    """
    Create a futures contract in the database.
    """
    conn = sqlite3.connect("marketmaker.db")
    cursor = conn.cursor()
    cursor.execute("""
    SELECT ID, CID, init_economy, premium, target_growth, return_rate
    FROM futures
    WHERE id = ?
    """, (user_id,))
    futures = cursor.fetchall()
    conn.close()
    
    if futures != []:
        return "You already have an ongoing option, wait for it to expire or cancel it with /canceloption."

    timestamp = datetime.now(timezone("US/Eastern"))
    if duration < timedelta(minutes = 0.1):
        return "All futures must be at least 15 minutes."

    if bet < 10:
        return "The minimum bet is 10$."

    if abs(target_growth) < 100:
        return "You must set your target to at least 100$."

    user_wallet = fetch_wallet_amount(user_id)
    if user_wallet < bet:
        return "You do not have enough money for this future."

    bonus_transfer(user_id, -bet, 11 if target_growth > 0 else 10)

    total_money = fetch_wallet_amount("TOTAL")
    end = timestamp + duration

    return_rate = (0.1 + math.log2(1 + abs(target_growth)/100)) * (1 + 0.5 * math.log2(1 + duration.seconds / 3600) ** 1.5) * bet/250
    break_even_growth = math.ceil(target_growth + bet/return_rate)

    conn = sqlite3.connect("marketmaker.db")
    cursor = conn.cursor()

    # Insert the futures contract into the database
    cursor.execute(
        """
        INSERT INTO futures (ID, CID, init_economy, end, premium, target_growth, return_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, channel_id, total_money, end, bet, target_growth, return_rate),
    )

    conn.commit()
    conn.close()

    return f"You have wagered {bet}$ for the economy to {"grow" if target_growth > 0 else "shrink"} by {abs(target_growth)}$ on {(timestamp + duration).strftime("%Y-%m-%d %H:%M")}.\nFor every 100$ the economy deviates past {abs(target_growth)}$ from its current value of {total_money}$, you will gain roughly {round(return_rate*100)}$.\nYour break-even point is {"an inflation" if target_growth > 0 else "a deflation"} of {break_even_growth}$."


def resolve_futures(
    user_id: int,
    init_economy,
    target_growth,
    return_rate,
):
    final_economy = fetch_wallet_amount("TOTAL")
    strike = init_economy + target_growth
    if target_growth > 0:
        final_return = max(math.floor((final_economy - strike) * return_rate), 0)
    else:
        final_return = max(math.floor((strike - final_economy) * return_rate), 0)

    if final_return == 0:
        return 0
    else:
        bonus_transfer(user_id, final_return, 13 if target_growth > 0 else 12)
        return final_return

def cancel_futures(user_id: int):
    conn = sqlite3.connect("marketmaker.db")
    cursor = conn.cursor()
    all_futures = cursor.execute("SELECT * FROM futures").fetchall()
    cursor.execute("DELETE FROM futures WHERE ID = ?", (user_id,))
    conn.commit()
    conn.close()