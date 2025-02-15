import os
import sqlite3
import string
from itertools import product
from pathlib import Path

from dotenv import load_dotenv
from nltk.corpus import words

STARTING_MONEY = 100000
DB_PATH = Path("marketmaker.db")  # relative to executable


def ensure_db() -> None:
    """Ensures that the storage database exists and is initialized."""

    if not DB_PATH.exists():
        economy = sqlite3.connect(DB_PATH)
        cur = economy.cursor()
        cur.execute("CREATE TABLE wallets(ID TEXT, cash INTEGER DEFAULT 0)")
        cur.execute("CREATE TABLE used_words(word TEXT)")
        cur.execute(
            """
            INSERT INTO wallets VALUES
                ('TOTAL', ?),
                ('BANK', ?)
        """,
            (STARTING_MONEY, STARTING_MONEY),
        )
        economy.commit()
        economy.close()


def ensure_substr() -> None:
    """Ensures that substring lists are initialized."""
    word_list = words.words()

    load_dotenv()

    static_dir = Path(__file__).parents[1] / "static"

    normal_min_words = int(os.getenv("NORMAL_MIN_WORDS"))
    hard_min_words = int(os.getenv("HARD_MIN_WORDS"))

    letters = list(string.ascii_lowercase)
    substrings = ["".join(i) for i in product(letters, repeat=2)] + [
        "".join(i) for i in product(letters, repeat=3)
    ]

    if not (fpath := static_dir / f"substr_normal_{normal_min_words}.txt").is_file():
        print(
            "Creating list of normal difficulty substrings, this can take several minutes..."
        )
        normal_substrings = []
        for i in substrings:
            if normal_min_words <= sum(i in s for s in word_list):
                normal_substrings.append(i)

        with fpath.open("w") as f:
            for s in normal_substrings:
                f.write(s + "\n")

    if not (fpath := static_dir / f"substr_hard_{hard_min_words}.txt").is_file():
        print(
            "Creating list of hard difficulty substrings, this can take several minutes..."
        )
        hard_substrings = []
        for i in substrings:
            if hard_min_words <= sum(i in s for s in word_list) < normal_min_words:
                hard_substrings.append(i)

        with fpath.open("w") as f:
            for s in hard_substrings:
                f.write(s + "\n")
