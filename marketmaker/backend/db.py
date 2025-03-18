from __future__ import annotations

import datetime
import math
import random
import sqlite3
from enum import Enum
from pathlib import Path
from typing import Literal

import pandas as pd
from pytz import timezone

DB_PATH = Path("marketmaker.db")  # relative to executable


class StatType(Enum):
    Tax = [6]
    Deflation = ["DEFLATION"]
    Inflation = [1, 8]
    Random = [7]
    Donation = [5]
    Puzzle = [2]
    Money = ["M"]


def generate_victim() -> tuple[str, int]:
    economy = sqlite3.connect(DB_PATH)
    cur = economy.cursor()

    cur.execute("""
    SELECT ID, cash
    FROM wallets
    WHERE ID NOT IN ("BANK", "TOTAL") AND cash > 1
    """)
    rows = cur.fetchall()
    economy.close()
    return random.choice(rows)


def fetch_wallet_amount(target_id: int | Literal["BANK", "TOTAL"]) -> int:
    economy = sqlite3.connect(DB_PATH)
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
    economy = sqlite3.connect(DB_PATH)
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
        cur.execute("UPDATE timeboard SET time = ?, word = ?, substr = ? WHERE ID = ?", (sol_time, word, substr, userid))

    economy.commit()
    economy.close()


def reset_timer_board_backend() -> None:
    economy = sqlite3.connect(DB_PATH)
    cur = economy.cursor()

    cur.execute("DROP TABLE IF EXISTS timeboard")
    cur.execute("CREATE TABLE timeboard(ID INTEGER PRIMARY KEY, time REAL, word TEXT, substr TEXT)")

    economy.commit()
    economy.close()


def tax_backend() -> None:
    print("Taxation time!")

    economy = sqlite3.connect(DB_PATH)
    cur = economy.cursor()
    cur.execute("SELECT ID FROM wallets WHERE ID NOT IN ('BANK', 'TOTAL')")
    userids = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT cash FROM wallets WHERE ID NOT IN ('BANK', 'TOTAL')")
    moneys = [row[0] for row in cur.fetchall()]
    economy.close()

    for userid, money in zip(userids, moneys):
        wallet_transfer_backend(userid, "BANK", math.ceil(0.05 * money), 6)


def wallet_transfer_backend(
    sendid: int | Literal["BANK"],
    recid: int | Literal["BANK"],
    amount: int,
    transaction: int,
) -> int:
    economy = sqlite3.connect(DB_PATH)
    cur = economy.cursor()

    sender_cash = fetch_wallet_amount(sendid)

    if sender_cash < amount:
        cur.execute("UPDATE wallets SET cash = ? WHERE ID = ?", (0, sendid))

        economy.commit()
        receiver_cash = fetch_wallet_amount(recid)

        cur.execute(
            "UPDATE wallets SET cash = ? WHERE ID = ?",
            (receiver_cash + sender_cash, recid),
        )
        result = sender_cash
    else:
        cur.execute(
            "UPDATE wallets SET cash = ? WHERE ID = ?", (sender_cash - amount, sendid)
        )

        economy.commit()
        receiver_cash = fetch_wallet_amount(recid)

        cur.execute(
            "UPDATE wallets SET cash = ? WHERE ID = ?", (receiver_cash + amount, recid)
        )
        result = amount

    timestamp = datetime.datetime.now(timezone("US/Eastern"))

    cur.execute(
        "INSERT INTO ledger (time, sender, receiver, amount, type) VALUES (?, ?, ?, ?, ?)",
        (timestamp, sendid, recid, amount, transaction),
    )

    economy.commit()
    economy.close()
    return result


def bonus_transfer(
    recid: int | Literal["BANK"], amount: int, transaction: int = 1,
) -> None:
    economy = sqlite3.connect(DB_PATH)
    cur = economy.cursor()

    receiver_cash = fetch_wallet_amount(recid)
    total_cash = fetch_wallet_amount("TOTAL")

    cur.execute(
        "UPDATE wallets SET cash = ? WHERE ID = ?", (receiver_cash + amount, recid)
    )
    cur.execute(
        "UPDATE wallets SET cash = ? WHERE ID = ?", (total_cash + amount, "TOTAL")
    )

    timestamp = datetime.datetime.now(timezone("US/Eastern"))

    cur.execute(
        "INSERT INTO ledger (time, sender, receiver, amount, type) VALUES (?, 'N/A', ?, ?, ?)",
        (timestamp, recid, amount, transaction),
    )

    economy.commit()
    economy.close()
    print(f"Gave {amount} to {recid} as a bonus.")


def add_used_word(word: str) -> None:
    economy = sqlite3.connect(DB_PATH)
    cur = economy.cursor()
    cur.execute("INSERT INTO used_words VALUES (?)", (word,))
    economy.commit()
    economy.close()

    print(f"Added {word} to used words.")


def leaderboard_backend() -> list:
    economy = sqlite3.connect(DB_PATH)
    cur = economy.cursor()

    cur.execute("""
    SELECT ID, cash
    FROM wallets
    WHERE ID NOT IN ("BANK", "TOTAL") AND cash > 0
    ORDER BY cash DESC
    LIMIT 10
    """)
    rows = cur.fetchall()

    economy.close()

    return rows


def build_ledger(targetid: int | Literal["BANK"]) -> list:
    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()

    cur.execute(
        """
    SELECT time, sender, receiver, amount, type
    FROM ledger
    WHERE sender IN (?) OR receiver IN (?)
    ORDER BY time DESC
    LIMIT 10
    """,
        (targetid, targetid),
    )

    rows = cur.fetchall()
    economy.close()
    return rows


def build_deflation_board() -> list:
    economy = sqlite3.connect("marketmaker.db")
    tt = pd.read_sql_query(
    """
    SELECT sender, receiver, amount, type
    FROM ledger
    WHERE type IN (7, 9)
    """,
    economy,
    )
    economy.close()

    deflation_rows = tt[(tt['amount'] < 0) & (tt["type"] == 9) & (tt["receiver"] == "BANK")]
    new_rows = []

    for idx, row in deflation_rows.iterrows():
        # Find the closest row above with type 7, receiver is BANK, and amount is -amount of type 9 row
        condition = (tt.index < idx) & (tt['type'] == 7) & (tt['receiver'] == 'BANK') & (tt['amount'] == -row['amount'])
        closest_row = tt[condition].iloc[-1:]  # Get the last (closest) row that matches the condition
        if not closest_row.empty:
            new_rows.append(closest_row)

    # Concatenate the new rows into a new DataFrame
    df = pd.concat(new_rows)

    # Swap the receiver and sender columns
    df = df.copy()
    df[['sender', 'receiver']] = df[['receiver', 'sender']]
    additional_rows = tt[(tt["type"] == 9) & (tt["receiver"] != "BANK")]
    additional_rows.loc[:, 'amount'] = -additional_rows['amount']  # Flip the sign of the amount column
    df = pd.concat([df, additional_rows])

    finalboard = df.groupby("receiver").sum().sort_values("amount", ascending=False).head(10).reset_index()
    return pd.DataFrame({"Winner": finalboard["receiver"], "Amount": finalboard["amount"]})

def build_board(stat: StatType) -> list:

    if stat == StatType.Deflation:
        return build_deflation_board()

    economy = sqlite3.connect("marketmaker.db")
    tt = pd.read_sql_query(
    """
    SELECT sender, receiver, amount
    FROM ledger
    WHERE type IN ({})
    """.format(','.join(['?'] * len(stat.value))),
    economy,
    params = tuple(stat.value),
    )
    economy.close()

    # Identify rows with negative amounts
    negative_amounts = tt['amount'] < 0

    # Swap sender and receiver for negative amounts
    tt.loc[negative_amounts, ['sender', 'receiver']] = tt.loc[negative_amounts, ['receiver', 'sender']].values

    # Change the sign of the negative amounts
    tt.loc[negative_amounts, 'amount'] = -tt.loc[negative_amounts, 'amount']

    sendrec_pre = {
        (StatType.Tax, StatType.Donation, StatType.Money, StatType.Random): "sender",
        (StatType.Inflation, StatType.Puzzle) : "receiver",
    }

    sendrec = {}
    for k, v in sendrec_pre.items():
        for key in k:
            sendrec[key] = v

    finalboard = tt.groupby(sendrec[stat]).sum().query(f'{sendrec[stat]} != "BANK"').sort_values("amount", ascending=False).head(10).reset_index()
    return pd.DataFrame({"Winner": finalboard[sendrec[stat]], "Amount": finalboard["amount"]})


def build_timetrial() -> list:
    economy = sqlite3.connect("marketmaker.db")
    cur = economy.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS timeboard(ID INTEGER PRIMARY KEY, time REAL, word TEXT, substr TEXT)")

    cur.execute("""
    SELECT ID, time, word, substr
    FROM timeboard
    ORDER BY time ASC
    LIMIT 3
    """)

    rows = cur.fetchall()

    economy.commit()
    economy.close()
    return rows
