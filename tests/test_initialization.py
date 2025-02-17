from pathlib import Path

import pytest

from marketmaker.initialization import ensure_db


def test_database_bootstrap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that ensure_db creates the database file if it does not exist.

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
