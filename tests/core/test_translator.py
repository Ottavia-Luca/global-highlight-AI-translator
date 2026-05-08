# tests/core/test_translator.py
import json
import asyncio
from unittest.mock import patch, AsyncMock


class FakeResponse:
    def __init__(self, status, data_lines):
        self.status = status
        self._lines = data_lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    @property
    def content(self):
        async def _read():
            return json.dumps({"choices": [{"message": {"content": "".join(
                self._lines
            )}}]}).encode()
        return _read()


def test_translator_builds_openai_payload():
    from core.translator import TranslatorService
    svc = TranslatorService(
        api_url="http://test/v1/chat/completions",
        api_key="sk-test",
        model="test-model",
        system_prompt="Translate accurately.",
        timeout=10,
        max_tokens=512,
    )
    payload, headers = svc._build_payload("hello")
    assert headers["Authorization"] == "Bearer sk-test"
    assert payload["model"] == "test-model"
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"
    assert payload["messages"][1]["content"] == "hello"
    assert payload["stream"] is True


def test_translator_parses_sse_chunk():
    from core.translator import TranslatorService
    svc = TranslatorService(
        api_url="http://test", api_key="sk-test", model="m",
        system_prompt="", timeout=10, max_tokens=512,
    )
    line = 'data: {"choices":[{"delta":{"content":"你好"}}]}'
    token = svc._parse_sse_line(line)
    assert token == "你好"


def test_translator_parses_sse_done():
    from core.translator import TranslatorService
    svc = TranslatorService(
        api_url="http://test", api_key="sk-test", model="m",
        system_prompt="", timeout=10, max_tokens=512,
    )
    assert svc._parse_sse_line("data: [DONE]") is None


def test_translator_parses_invalid_line():
    from core.translator import TranslatorService
    svc = TranslatorService(
        api_url="http://test", api_key="sk-test", model="m",
        system_prompt="", timeout=10, max_tokens=512,
    )
    assert svc._parse_sse_line("") is None
    assert svc._parse_sse_line("not a data line") is None
