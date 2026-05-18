"""Shared pytest fixtures."""
import json
import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture(fixtures_dir):
    def _load(name: str):
        with open(fixtures_dir / name) as f:
            return json.load(f)
    return _load
