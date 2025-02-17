from pathlib import Path

import pytest
import sqlite3
import os

from marketmaker.initialization import ensure_db, STARTING_MONEY, num_member_words
from nltk.corpus import words


def test_database_bootstrap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that ensure_db creates the database file if it does not exist, and that the produced substring txt files are valid.

    Fixtures
    --------
    tmp_path : Path
        A temporary directory created by pytest.
    monkeypatch : pytest.MonkeyPatch
        A pytest fixture that allows for monkeypatching.
    """

    # monkeypatch DB_PATH to point to tmp_path/marketmaker.db (test directory)
    monkeypatch.setattr(
        "marketmaker.initialization.DB_PATH", tmp_path / "marketmaker.db"
    )

    # ensure tmp_path/marketmaker.db does not exist
    assert not (tmp_path / "marketmaker.db").exists()
    ensure_db()
    assert (tmp_path / "marketmaker.db").exists()
    
    economy = sqlite3.connect(tmp_path / "marketmaker.db")
    cur = economy.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    tables = [name[0] for name in cur.fetchall()]
    
    assert "wallets" in tables
    assert "used_words" in tables
    assert "ledger" in tables

    cur.execute("SELECT cash FROM wallets WHERE ID = 'BANK'")
    bank_money = cur.fetchone()[0]
    assert bank_money == STARTING_MONEY
    
    cur.execute("SELECT cash FROM wallets WHERE ID = 'TOTAL'")
    total_money = cur.fetchone()[0]
    assert total_money == STARTING_MONEY
    
    economy.close()
    
    root = Path(__file__).parents[1]
    normal_min_env = os.getenv("NORMAL_MIN_WORDS")
    if normal_min_env is None:
        raise Exception("No NORMAL_MIN_WORDS provided in .env file.")
    normal_min_words = int(normal_min_env)
    with open(f"{root}/static/substr_normal_{normal_min_words}.txt", "r") as f:
        normal_substrings: list[str] = [line.rstrip("\n") for line in f]
        
    for substr in normal_substrings:
        assert num_member_words(substr, words.words()) >= normal_min_words
        
    hard_min_env = os.getenv("HARD_MIN_WORDS")
    if hard_min_env is None:
        raise Exception("No HARD_MIN_WORDS provided in .env file.")
    hard_min_words = int(hard_min_env)
    with open(f"{root}/static/substr_hard_{hard_min_words}.txt", "r") as f:
        hard_substrings: list[str] = [line.rstrip("\n") for line in f]
        
    for substr in hard_substrings:
        assert normal_min_words > num_member_words(substr, words.words()) >= hard_min_words