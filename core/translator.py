import json
import asyncio
import ssl
import logging
from urllib.parse import urlparse
from PyQt6.QtCore import QThread, pyqtSignal

import aiohttp

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
        self._translate_task = None
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
        connector = aiohttp.TCPConnector(limit=1, keepalive_timeout=30, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(connect=5.0, sock_read=self._timeout)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            await self._warmup()
            while not self._quit_flag:
                text = await self._next_text()
                if text:
                    await self._run_translate(session, text)

    async def _next_text(self):
        """Wait for and return the next text to translate, or None on quit."""
        text = self._pending_text
        self._pending_text = None
        if text:
            return text
        await self._text_event.wait()
        self._text_event.clear()
        if self._quit_flag:
            return None
        text = self._pending_text
        self._pending_text = None
        return text

    async def _run_translate(self, session, text):
        self._translate_task = asyncio.create_task(self._do_translate(session, text))
        try:
            await self._translate_task
        except asyncio.CancelledError:
            pass
        finally:
            self._translate_task = None

    async def _warmup(self):
        """仅预建 TCP+TLS 连接，不发 HTTP 请求，不消耗 API 额度。"""
        if not self._api_key:
            return
        try:
            url = urlparse(self._api_url)
            host = url.hostname
            port = url.port or 443
            _log.info("预热连接 %s:%d ...", host, port)
            ctx = ssl.create_default_context()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=ctx),
                timeout=5.0,
            )
            writer.close()
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

    def cancel(self):
        had_pending = self._pending_text is not None
        self._pending_text = None
        task = self._translate_task
        if task is not None and not task.done():
            _log.info("[取消] 翻译进行中，中断请求")
            try:
                self._loop.call_soon_threadsafe(task.cancel)
            except Exception:
                pass
        elif had_pending:
            _log.info("[取消] 翻译排队中，已丢弃")

    def _build_payload(self, text):
        payload = {
            "model": self._model,
            "messages": [
                {"role": "user", "content": (
                    f"<instruction>{self._system_prompt}</instruction>\n"
                    f"<text>{text}</text>"
                )},
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
