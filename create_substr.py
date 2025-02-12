from nltk.corpus import words
word_list = words.words()

import json
import itertools
import string

max_words = 250
min_words = 100

letters = list(string.ascii_lowercase)
substrings = ["".join(i) for i in itertools.product(letters, repeat = 2)] + ["".join(i) for i in itertools.product(letters, repeat = 3)]

good_substrings = []
for i in substrings:
    if min_words <= sum(i in s for s in word_list) < max_words:
        good_substrings.append(i)

with open(f"substr_{min_words}.txt", "w") as f:
    for s in good_substrings:
        f.write(s + '\n')