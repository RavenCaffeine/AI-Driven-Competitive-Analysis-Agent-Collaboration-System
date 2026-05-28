"""Tests for memory storage system."""

import json
import tempfile
from pathlib import Path
from competitive_analysis.memory.storage import MemoryStorage, create_empty_memory


def test_create_empty_memory():
    mem = create_empty_memory()
    assert mem["version"] == "1.0"
    assert "facts" in mem
    assert "competitor_history" in mem


def test_memory_save_and_load(tmp_path):
    storage_path = str(tmp_path / "test_memory.json")
    storage = MemoryStorage(storage_path=storage_path)

    # Load empty
    mem = storage.load()
    assert mem["version"] == "1.0"

    # Save and reload
    mem["facts"].append({"fact": "test fact", "confidence": 0.9})
    storage.save(mem)

    mem2 = storage.load()
    assert len(mem2["facts"]) == 1
    assert mem2["facts"][0]["fact"] == "test fact"


def test_add_fact(tmp_path):
    storage = MemoryStorage(storage_path=str(tmp_path / "mem.json"))
    storage.add_fact("Notion launched AI features in 2023", confidence=0.85, source="https://notion.so")

    mem = storage.load()
    assert len(mem["facts"]) == 1
    assert mem["facts"][0]["confidence"] == 0.85


def test_dedup_facts(tmp_path):
    storage = MemoryStorage(storage_path=str(tmp_path / "mem.json"))
    storage.add_fact("Notion has AI", confidence=0.7)
    storage.add_fact("Notion has AI", confidence=0.9)  # should update, not duplicate

    mem = storage.load()
    assert len(mem["facts"]) == 1
    assert mem["facts"][0]["confidence"] == 0.9  # takes max


def test_competitor_history(tmp_path):
    storage = MemoryStorage(storage_path=str(tmp_path / "mem.json"))
    storage.update_competitor_history("Notion", {"pricing": "$8/mo"})
    storage.update_competitor_history("Notion", {"pricing": "$10/mo"})

    mem = storage.load()
    assert len(mem["competitor_history"]["Notion"]) == 2
