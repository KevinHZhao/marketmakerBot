from nltk.corpus import words
word_list = words.words()

import json
import itertools
import string

min_words = 250

letters = list(string.ascii_lowercase)
substrings = ["".join(i) for i in itertools.product(letters, repeat = 2)] + ["".join(i) for i in itertools.product(letters, repeat = 3)]

good_substrings = []
for i in substrings:
    if sum(i in s for s in word_list) >= min_words:
        good_substrings.append(i)

with open(f"substr_{min_words}.txt", "w") as f:
    for s in good_substrings:
        f.write(s + '\n')