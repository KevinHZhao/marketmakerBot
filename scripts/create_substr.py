from nltk.corpus import words
from dotenv import load_dotenv
from pathlib import Path
import itertools
import string
import os

def main() -> None:
    word_list = words.words()

    load_dotenv()

    root = Path(__file__).parents[1]

    normal_min_words = int(os.getenv("NORMAL_MIN_WORDS"))
    hard_min_words = int(os.getenv("HARD_MIN_WORDS"))

    letters = list(string.ascii_lowercase)
    substrings = ["".join(i) for i in itertools.product(letters, repeat = 2)] + ["".join(i) for i in itertools.product(letters, repeat = 3)]

    if not Path(f"{root}/static/substr_normal_{normal_min_words}.txt").is_file():
        print("Creating list of normal difficulty substrings, this can take several minutes...")
        normal_substrings = []
        for i in substrings:
            if normal_min_words <= sum(i in s for s in word_list):
                normal_substrings.append(i)

        with open(f"{root}/static/substr_normal_{normal_min_words}.txt", "w") as f:
            for s in normal_substrings:
                f.write(s + '\n')

    if not Path(f"{root}/static/substr_hard_{hard_min_words}.txt").is_file():
        print("Creating list of hard difficulty substrings, this can take several minutes...")
        hard_substrings = []
        for i in substrings:
            if hard_min_words <= sum(i in s for s in word_list) < normal_min_words:
                hard_substrings.append(i)

        with open(f"{root}/static/substr_hard_{hard_min_words}.txt", "w") as f:
            for s in hard_substrings:
                f.write(s + '\n')