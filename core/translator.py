import json
import asyncio
import aiohttp
import logging
from PyQt6.QtCore import QThread, pyqtSignal

_log = logging.getLogger("translator")


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
        self._text_event = None
        self._quit_flag = False
        self.start()

    def translate(self, text):
        self._pending_text = text
        try:
            if self._text_event and self._loop:
                self._loop.call_soon_threadsafe(self._text_event.set)
        except Exception:
            pass

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._text_event = asyncio.Event()
        self._loop.run_until_complete(self._run_loop())

    async def _run_loop(self):
        connector = aiohttp.TCPConnector(limit=1, keepalive_timeout=30)
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            await self._warmup(session)
            # 预热期间可能已有文字排队
            if self._pending_text:
                text = self._pending_text
                self._pending_text = None
                if text:
                    await self._do_translate(session, text)
            while not self._quit_flag:
                await self._text_event.wait()
                self._text_event.clear()
                if self._quit_flag:
                    break
                text = self._pending_text
                self._pending_text = None
                if text:
                    await self._do_translate(session, text)

    async def _warmup(self, session):
        if not self._api_key:
            return
        try:
            _log.info("预热 API 连接...")
            payload, headers = self._build_payload("Hi")
            async with session.post(
                self._api_url, json=payload, headers=headers
            ) as resp:
                if resp.status == 200:
                    async for _ in resp.content:
                        break
            _log.info("预热完成")
        except Exception:
            _log.info("预热跳过（网络不可达）")

    async def _do_translate(self, session, text):
        payload, headers = self._build_payload(text)
        try:
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

    def stop(self):
        self._quit_flag = True
        if self._text_event and self._loop:
            self._loop.call_soon_threadsafe(self._text_event.set)
        self.wait()
