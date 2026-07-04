"""本地 Mock LLM 服务器，用于 E2E 测试阶段一。

提供 OpenAI 兼容的 /v1/models 与 /v1/chat/completions 端点，
将最后一条 user 消息原样作为 assistant 回复返回，避免调用真实 LLM。
"""

from __future__ import annotations

import time
from typing import Any

from aiohttp import web


class MockLLMServer:
    """OpenAI 兼容的 mock LLM 服务器。"""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self._host = host
        self._port = port
        self._runner: web.AppRunner | None = None
        self._base_url = ""

    @property
    def base_url(self) -> str:
        """返回服务器 base URL，需在 start 之后访问。"""
        return self._base_url

    async def _models_handler(self, request: web.Request) -> web.Response:
        """返回 mock 模型列表。"""
        return web.json_response(
            {
                "object": "list",
                "data": [
                    {
                        "id": "anp-echo-model",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "anp-e2e",
                    }
                ],
            }
        )

    async def _chat_handler(self, request: web.Request) -> web.Response:
        """将最后一条 user 消息内容作为 assistant 回复返回。"""
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "invalid json"}, status=400)

        messages = body.get("messages", [])
        echo = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    echo = content
                break

        model = body.get("model", "anp-echo-model")
        stream = body.get("stream", False)

        if not stream:
            response: dict[str, Any] = {
                "id": "chatcmpl-anp-e2e",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": echo},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
            return web.json_response(response)

        # Streaming SSE response
        import json as _json

        resp = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
        await resp.prepare(request)
        created = int(time.time())
        for char in echo:
            payload = {
                "id": "chatcmpl-anp-e2e",
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {"content": char}, "finish_reason": None}],
            }
            await resp.write(f"data: {_json.dumps(payload)}\n\n".encode())
        payload = {
            "id": "chatcmpl-anp-e2e",
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        await resp.write(f"data: {_json.dumps(payload)}\n\n".encode())
        await resp.write(b"data: [DONE]\n\n")
        return resp

    async def start(self) -> str:
        """启动服务器并返回 base URL。"""
        app = web.Application()
        app.router.add_get("/v1/models", self._models_handler)
        app.router.add_post("/v1/chat/completions", self._chat_handler)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()

        actual_port = self._port
        if actual_port == 0:
            addresses = self._runner.addresses
            if addresses:
                actual_port = addresses[0][1]
            else:
                raise RuntimeError("Mock LLM 服务器未能绑定到可用端口")

        self._base_url = f"http://{self._host}:{actual_port}"
        return self._base_url

    async def stop(self) -> None:
        """停止服务器。"""
        if self._runner is not None:
            await self._runner.cleanup()
            self._base_url = ""
            self._runner = None

    async def __aenter__(self) -> MockLLMServer:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
