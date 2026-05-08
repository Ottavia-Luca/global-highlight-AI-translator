import json
import asyncio
import aiohttp
from PyQt6.QtCore import QThread, pyqtSignal


class TranslatorService(QThread):
    token_received = pyqtSignal(str)
    translation_done = pyqtSignal(str)
    translation_error = pyqtSignal(str)

    def __init__(self, api_url, api_key, model, system_prompt, timeout, max_tokens):
        super().__init__()
        self._api_url = api_url
        self._api_key = api_key
        self._model = model
        self._system_prompt = system_prompt
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._pending_text = None
        self._loop = None

    def translate(self, text):
        self._pending_text = text
        if not self.isRunning():
            self.start()

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        while self._pending_text is not None:
            text = self._pending_text
            self._pending_text = None
            self._loop.run_until_complete(self._do_translate(text))

    async def _do_translate(self, text):
        payload, headers = self._build_payload(text)
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self._api_url, json=payload, headers=headers
                ) as resp:
                    if resp.status != 200:
                        if resp.status in (429, 500, 502, 503):
                            self.translation_error.emit(f"HTTP {resp.status}")
                        return
                    full_text = ""
                    async for line in resp.content:
                        decoded = line.decode("utf-8").strip()
                        token = self._parse_sse_line(decoded)
                        if token:
                            full_text += token
                            self.token_received.emit(token)
                    if full_text:
                        self.translation_done.emit(full_text)
        except (asyncio.TimeoutError, aiohttp.ClientError):
            self.translation_error.emit("network_error")

    def _build_payload(self, text):
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": text},
            ],
            "stream": True,
            "max_tokens": self._max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        return payload, headers

    def _parse_sse_line(self, line):
        if not line.startswith("data: "):
            return None
        data = line[6:]
        if data == "[DONE]":
            return None
        try:
            obj = json.loads(data)
            return obj["choices"][0]["delta"].get("content", "")
        except (json.JSONDecodeError, KeyError, IndexError):
            return None
