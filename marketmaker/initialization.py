import os
import sqlite3
from functools import partial
from itertools import product
from multiprocessing import Pool
from pathlib import Path
from string import ascii_lowercase

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


def num_member_words(substr: str, word_list: list[str]) -> int:
    """Returns the number of words in the nltk corpus that contain the given substring."""
    return sum(substr in word for word in word_list)


def ensure_substr() -> None:
    """Ensures that substring lists are initialized."""
    load_dotenv()

    static_dir = Path(__file__).parents[1] / "static"

    normal_min_words = int(os.getenv("NORMAL_MIN_WORDS"))
    hard_min_words = int(os.getenv("HARD_MIN_WORDS"))

    # Check if we need to create the lists
    normal_fpath = static_dir / f"substr_normal_{normal_min_words}.txt"
    hard_fpath = static_dir / f"substr_hard_{hard_min_words}.txt"
    require_create = not normal_fpath.is_file() or not hard_fpath.is_file()

    if not require_create:
        print("Substring lists are up to date.")
        return

    print("Creating substring lists, this can take several minutes...")
    substrings = ["".join(i) for i in product(ascii_lowercase, repeat=2)] + [
        "".join(i) for i in product(ascii_lowercase, repeat=3)
    ]

    # Determine counts of words containing each substring
    with Pool() as pool:
        substr_counts = pool.map(
            partial(num_member_words, word_list=words.words()),
            substrings,
            chunksize=50,
        )

    if not normal_fpath.is_file():
        print("Creating list of normal difficulty substrings...")
        normal_substrings = [
            substrings[i]
            for i in range(len(substrings))
            if substr_counts[i] >= normal_min_words
        ]

        with normal_fpath.open("w") as f:
            for s in normal_substrings:
                f.write(s + "\n")

    if not hard_fpath.is_file():
        print("Creating list of hard difficulty substrings...")
        hard_substrings = [
            substrings[i]
            for i in range(len(substrings))
            if substr_counts[i] >= hard_min_words
        ]

        with hard_fpath.open("w") as f:
            for s in hard_substrings:
                f.write(s + "\n")
