import sqlite3
from functools import partial
from itertools import product
from multiprocessing import Pool
from pathlib import Path
from string import ascii_lowercase

import nltk
import numpy as np

nltk.download("words")
nltk.download("wordnet")

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
        cur.execute("CREATE TABLE ledger(time TIMESTAMP, sender TEXT, receiver TEXT, amount INTEGER, type INTEGER)")
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


def create_substr(substr_counts: list[int], substrings: list[str], fpath: Path, difficulty: str, min_words: int = 0, max_words: float = float("inf")) -> None:
    if not fpath.is_file():
        print(f"Creating list of {difficulty} difficulty substrings...")
        good_substrings = [
            substrings[i]
            for i in range(len(substrings))
            if min_words <= substr_counts[i] < max_words
        ]

        with fpath.open("w") as f:
            for s in good_substrings:
                f.write(s + "\n")


def generate_counts(substrings: list[str], fpath: Path) -> None:
    # Determine counts of words containing each substring
    print("Creating substring counts...")
    with Pool() as pool:
        substr_counts = pool.map(
            partial(num_member_words, word_list=words.words()),
            substrings,
            chunksize=50,
        )
    np.savetxt(fpath, substr_counts, fmt="%s")


def ensure_substr(normal_min_words: int, hard_min_words: int) -> None:
    """Ensures that substring lists are initialized."""
    static_dir = Path(__file__).parents[1] / "static"

    # Check if we need to create the lists
    count_fpath = static_dir / "counts_substr.txt"
    normal_fpath = static_dir / f"substr_normal_{normal_min_words}.txt"
    hard_fpath = static_dir / f"substr_hard_{hard_min_words}.txt"
    require_create = not normal_fpath.is_file() or not hard_fpath.is_file()

    if not require_create:
        print("Substring lists are up to date.")
        return

    substrings = ["".join(i) for i in product(ascii_lowercase, repeat=2)] + [
        "".join(i) for i in product(ascii_lowercase, repeat=3)
    ]
    if not count_fpath.is_file():
        generate_counts(substrings, count_fpath)

    substr_counts: list[int] = np.loadtxt(count_fpath, dtype = int).tolist()

    create_substr(substr_counts, substrings, normal_fpath, "medium", normal_min_words)
    create_substr(substr_counts, substrings, hard_fpath, "hard", hard_min_words, normal_min_words)
