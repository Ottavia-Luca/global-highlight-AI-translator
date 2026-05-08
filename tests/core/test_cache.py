import os
import tempfile
import time


def test_cache_set_and_get():
    from core.cache import TranslationCache
    db_path = tempfile.mktemp(suffix='.db')
    try:
        cache = TranslationCache(db_path)
        cache.set("hello", "你好")
        result = cache.get("hello")
        assert result == "你好"
        cache.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_cache_miss_returns_none():
    from core.cache import TranslationCache
    db_path = tempfile.mktemp(suffix='.db')
    try:
        cache = TranslationCache(db_path)
        assert cache.get("nonexistent") is None
        cache.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_cache_auto_creates_table():
    from core.cache import TranslationCache
    db_path = tempfile.mktemp(suffix='.db')
    try:
        cache = TranslationCache(db_path)
        cache.set("test", "测试")
        assert cache.count() == 1
        cache.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_cache_prunes_by_max_entries():
    from core.cache import TranslationCache
    db_path = tempfile.mktemp(suffix='.db')
    try:
        cache = TranslationCache(db_path, max_entries=3)
        for i in range(5):
            cache.set(f"text_{i}", f"翻译_{i}")
        assert cache.count() <= 3
        cache.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_cache_prunes_by_ttl():
    from core.cache import TranslationCache
    db_path = tempfile.mktemp(suffix='.db')
    try:
        cache = TranslationCache(db_path, max_entries=100, ttl_days=0)
        cache.set("old", "旧")
        assert cache.get("old") is None
        cache.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_cache_persistence():
    from core.cache import TranslationCache
    db_path = tempfile.mktemp(suffix='.db')
    try:
        cache1 = TranslationCache(db_path)
        cache1.set("persist", "持久化")
        cache1.close()

        cache2 = TranslationCache(db_path)
        assert cache2.get("persist") == "持久化"
        cache2.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_cache_saves_bookmark():
    from core.cache import TranslationCache
    db_path = tempfile.mktemp(suffix='.db')
    try:
        cache = TranslationCache(db_path)
        cache.save_bookmark("hello", "你好")
        bookmarks = cache.get_bookmarks()
        assert len(bookmarks) == 1
        assert bookmarks[0][0] == "hello"
        assert bookmarks[0][1] == "你好"
        cache.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
