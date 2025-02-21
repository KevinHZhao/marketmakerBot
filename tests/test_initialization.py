import sqlite3
from pathlib import Path

import pytest

from marketmaker.initialization import STARTING_MONEY, ensure_db


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
