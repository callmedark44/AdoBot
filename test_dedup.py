"""Tests for the ported dedup store + the bot's top-up round decision.

Run: pytest test_dedup.py
"""
import os

from PIL import Image

import bot
import dedup_store


def _make_image(path, kind):
    img = Image.new("RGB", (96, 96))
    px = img.load()
    for x in range(96):
        for y in range(96):
            if kind == "a":
                px[x, y] = (255, (x * y) % 256, 0)
            else:
                px[x, y] = (0, x % 256, y % 256)
    img.save(path)


def test_duplicate_detected_across_reuploads(tmp_path):
    store = dedup_store.DedupStore(db_path=str(tmp_path / "dedup.sqlite3"))
    a, b = str(tmp_path / "a.png"), str(tmp_path / "b.png")
    _make_image(a, "a")
    _make_image(b, "a")  # same pixels, different filename = cross-site re-upload

    first = store.check_and_add(a, site="danbooru")
    second = store.check_and_add(b, site="safebooru")
    assert not first.is_duplicate
    assert second.is_duplicate
    assert second.matched_path == a
    store.close()


def test_different_image_not_duplicate(tmp_path):
    store = dedup_store.DedupStore(db_path=str(tmp_path / "dedup.sqlite3"))
    a, c = str(tmp_path / "a.png"), str(tmp_path / "c.png")
    _make_image(a, "a")
    _make_image(c, "c")

    store.check_and_add(a, site="danbooru")
    assert not store.check_and_add(c, site="danbooru").is_duplicate
    store.close()


def test_record_outlives_deleted_file(tmp_path):
    """Bot-specific: files are deleted right after Telegram sends them, so a
    phantom record must keep deduping (Rems-Dl would prune it and re-serve)."""
    store = dedup_store.DedupStore(db_path=str(tmp_path / "dedup.sqlite3"))
    a, b = str(tmp_path / "a.png"), str(tmp_path / "b.png")
    _make_image(a, "a")
    store.check_and_add(a, site="danbooru")
    os.remove(a)  # sent to Telegram, file gone
    _make_image(b, "a")  # same image re-served later

    assert store.check_and_add(b, site="safebooru").is_duplicate
    store.close()


def test_topup_round_decision():
    target, cap = 5, bot.MAX_FETCH_ROUNDS
    assert bot._next_round(target, queued=4, killed=1, round_no=0) == 1  # fetch 1 more
    assert bot._next_round(target, queued=5, killed=3, round_no=0) == 0  # user satisfied
    assert bot._next_round(target, queued=4, killed=0, round_no=0) == 0  # nothing killed: stop
    assert bot._next_round(target, queued=3, killed=2, round_no=cap - 1) == 0  # round cap
