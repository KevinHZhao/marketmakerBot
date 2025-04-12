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
    SELECT *
    FROM futures
    WHERE id = ?
    """, (user_id,))
    futures = cursor.fetchall()
    conn.close()
    
    if futures != []:
        return "You already have an ongoing option, wait for it to expire or cancel it with /canceloption."

    timestamp = datetime.now(timezone("US/Eastern"))
    if duration < timedelta(minutes = 15):
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

    max_gain = round((1 + math.log2(1 + abs(target_growth)/(total_money+bet))) * (1 + 0.5 * math.log2(1 + duration.total_seconds() / 3600) ** 1.5) * bet)
    break_even_growth = math.ceil(-math.log(2 * max_gain / (bet + max_gain) - 1)*10/(0.1 + math.log2(1 + abs(target_growth)/(total_money+bet))))

    conn = sqlite3.connect("marketmaker.db")
    cursor = conn.cursor()

    # Insert the futures contract into the database
    cursor.execute(
        """
        INSERT INTO futures (ID, CID, init_economy, duration, end, premium, target_growth)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, channel_id, total_money, int(duration.total_seconds()), end, bet, target_growth),
    )

    conn.commit()
    conn.close()

    return f"You have wagered {bet}$ for the economy to {"grow" if target_growth > 0 else "shrink"} by {abs(target_growth)}$ on {(timestamp + duration).strftime("%Y-%m-%d %H:%M")}.\nYou can gain at most {max_gain}$ from this wager, for a maximum profit of {max_gain - bet}$.\nYour break-even point is {"an inflation" if target_growth > 0 else "a deflation"} of {abs(target_growth + break_even_growth)}$ on the current economy of {total_money}$."


def resolve_futures(
    user_id: int,
    init_economy,
    target_growth,
    bet,
    duration,
):
    final_economy = fetch_wallet_amount("TOTAL")
    strike = init_economy + target_growth
    if target_growth > 0:
        final_diff = max(final_economy - strike, 0)
    else:
        final_diff = max(strike - final_economy, 0)

    if final_diff == 0:
        return 0
    else:
        max_gain = round((1 + math.log2(1 + abs(target_growth)/(init_economy+bet))) * (1 + 0.5 * math.log2(1 + duration / 3600) ** 1.5) * bet)
        final_return = round(2 * max_gain / (1 + math.exp(-final_diff*(0.1 + math.log2(1 + abs(target_growth)/(init_economy+bet)))/10)) - max_gain)
        bonus_transfer(user_id, final_return, 13 if target_growth > 0 else 12)
        return final_return

def cancel_futures(user_id: int):
    conn = sqlite3.connect("marketmaker.db")
    cursor = conn.cursor()
    all_futures = cursor.execute("SELECT * FROM futures").fetchall()
    cursor.execute("DELETE FROM futures WHERE ID = ?", (user_id,))
    conn.commit()
    conn.close()
