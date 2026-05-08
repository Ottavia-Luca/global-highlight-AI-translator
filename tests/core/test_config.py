# tests/core/test_config.py
import tempfile
import os
import time
from pathlib import Path


def test_config_loads_yaml():
    from core.config import Config
    yaml_content = """
api:
  key: "test-key"
  model: "test-model"
translation:
  auto_detect: false
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        cfg = Config(tmp_path)
        assert cfg.api_key == "test-key"
        assert cfg.api_model == "test-model"
        assert cfg.auto_detect is False
    finally:
        os.unlink(tmp_path)


def test_config_defaults_when_file_missing():
    from core.config import Config
    cfg = Config("/nonexistent/path/config.yaml")
    assert cfg.api_url == "https://api.deepseek.com/v1/chat/completions"
    assert cfg.cache_max_entries == 10000
    assert cfg.hover_delay == 200


def test_config_hot_reload():
    from core.config import Config
    yaml_content = 'api:\n  key: "old-key"\n'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        cfg = Config(tmp_path)
        assert cfg.api_key == "old-key"

        with open(tmp_path, 'w') as f:
            f.write('api:\n  key: "new-key"\n')
        cfg.reload()
        assert cfg.api_key == "new-key"
    finally:
        os.unlink(tmp_path)
