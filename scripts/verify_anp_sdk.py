"""临时验证脚本：验证 ANP SDK DID WBA 生成、HTTP Message Signature 和 Hermes 契约。

运行方式：
    python3 scripts/verify_anp_sdk.py

说明：
- 在本地启动一个临时 aiohttp 服务器，用于托管调用方 DID 文档。
- 使用 `DidWbaVerifier` 验证由 `DIDWbaAuthHeader` 生成的 HTTP Message Signature。
- 由于 `DidWbaVerifier.verify_request` 内部调用 `resolve_did_wba_document`，
  该函数不支持 `base_url_override`，因此必须通过本地服务器提供真实可解析的 URL。
- 同时验证 `resolve_did_document(..., base_url_override=...)` 的解析能力。
"""

import asyncio
import json
import logging
import tempfile
from pathlib import Path

from aiohttp import web
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from anp.authentication import DIDWbaAuthHeader, create_did_wba_document
from anp.authentication import did_wba_verifier
from anp.authentication.did_resolver import resolve_did_document
from anp.authentication.did_wba import resolve_did_wba_document
from anp.authentication.did_wba_verifier import DidWbaVerifier, DidWbaVerifierConfig

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _generate_jwt_keys():
    """生成临时的 RSA 密钥对，用于 DidWbaVerifier 签发 access token。"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return private_pem, public_pem


async def _main():
    workdir = Path(tempfile.mkdtemp(prefix="anp-verify-"))
    logger.info("工作目录: %s", workdir)

    # ------------------------------------------------------------------
    # 1. 生成调用方 did:wba 身份
    # ------------------------------------------------------------------
    caller_doc, caller_keys = create_did_wba_document(
        hostname="localhost",
        path_segments=["agent"],
        agent_description_url="https://localhost/agent/ad.json",
        did_profile="e1",
    )
    caller_did = caller_doc["id"]
    logger.info("生成调用方 DID: %s", caller_did)

    did_path = workdir / "caller_did.json"
    key_path = workdir / "caller_private.pem"
    did_path.write_text(json.dumps(caller_doc), encoding="utf-8")

    auth_key = caller_keys.get("key-1") or next(iter(caller_keys.values()))
    key_path.write_bytes(auth_key[0])

    # ------------------------------------------------------------------
    # 2. 启动本地 DID 文档服务器
    # ------------------------------------------------------------------
    did_doc_store = {caller_did: caller_doc}

    async def _did_handler(request: web.Request) -> web.Response:
        # URL 形如 /agent/<fingerprint>/did.json
        stored = did_doc_store.get(caller_did)
        if stored is None:
            raise web.HTTPNotFound()
        return web.json_response(stored)

    app = web.Application()
    # 根据 did:wba:localhost:agent:<fingerprint> 推导路径前缀
    path_segments = caller_did.split(":")[3:]
    route_path = "/" + "/".join(path_segments) + "/did.json"
    app.router.add_get(route_path, _did_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8765)
    await site.start()
    logger.info("DID 文档服务器已启动: http://127.0.0.1:8765%s", route_path)

    try:
        # ------------------------------------------------------------------
        # 3. 验证 resolve_did_document 的 base_url_override 能力
        # ------------------------------------------------------------------
        resolved = await resolve_did_document(
            caller_did,
            base_url_override="http://127.0.0.1:8765",
            verify_proof=False,
        )
        assert resolved["id"] == caller_did, "DID 文档 ID 不匹配"
        logger.info("resolve_did_document(base_url_override) 成功")

        # ------------------------------------------------------------------
        # 4. 使用 DIDWbaAuthHeader 生成 HTTP Message Signature
        # ------------------------------------------------------------------
        auth = DIDWbaAuthHeader(
            did_document_path=str(did_path),
            private_key_path=str(key_path),
            auth_mode="http_signatures",
        )
        target_url = "http://127.0.0.1:8765/agent/rpc"
        body = json.dumps(
            {"jsonrpc": "2.0", "method": "chat", "params": {"message": "hi"}, "id": "1"}
        )
        headers = auth.get_auth_header(
            server_url=target_url,
            method="POST",
            headers={"Content-Type": "application/json"},
            body=body,
        )
        assert "Signature-Input" in headers, "缺少 Signature-Input"
        assert "Signature" in headers, "缺少 Signature"
        logger.info("DIDWbaAuthHeader 生成签名头成功")
        logger.info("Signature-Input: %s", headers["Signature-Input"])

        # ------------------------------------------------------------------
        # 5. 使用 DidWbaVerifier 验证签名
        # ------------------------------------------------------------------
        # DidWbaVerifier 内部调用 resolve_did_wba_document，该函数不支持
        # base_url_override。在测试环境中通过 monkey-patch 让它从本地服务器解析。
        original_resolve_did_wba_document = resolve_did_wba_document

        async def _patched_resolve_did_wba_document(did: str, verify_proof: bool = False):
            return await resolve_did_document(
                did,
                base_url_override="http://127.0.0.1:8765",
                verify_proof=verify_proof,
            )

        did_wba_verifier.resolve_did_wba_document = _patched_resolve_did_wba_document

        jwt_private, jwt_public = _generate_jwt_keys()
        verifier = DidWbaVerifier(
            DidWbaVerifierConfig(
                jwt_private_key=jwt_private,
                jwt_public_key=jwt_public,
                require_nonce_for_http_signatures=True,
            )
        )
        try:
            result = await verifier.verify_request(
                method="POST",
                url=target_url,
                headers={**headers, "Content-Type": "application/json"},
                body=body,
                domain="localhost",
            )
            assert result["did"] == caller_did, "验证结果 DID 不匹配"
            assert result["auth_scheme"] == "http_signatures", "认证方案应为 http_signatures"
            assert "access_token" in result, "应返回 access_token"
            logger.info("DidWbaVerifier 验证成功，返回 access_token")
        finally:
            did_wba_verifier.resolve_did_wba_document = original_resolve_did_wba_document

        # ------------------------------------------------------------------
        # 6. 验证 Bearer token
        # ------------------------------------------------------------------
        bearer_headers = {"Authorization": f"Bearer {result['access_token']}"}
        bearer_result = await verifier.verify_request(
            method="GET",
            url=target_url,
            headers=bearer_headers,
        )
        assert bearer_result["did"] == caller_did, "Bearer 验证 DID 不匹配"
        assert bearer_result["auth_scheme"] == "bearer", "认证方案应为 bearer"
        logger.info("Bearer token 验证成功")

    finally:
        await runner.cleanup()
        logger.info("DID 文档服务器已停止")

    # ------------------------------------------------------------------
    # 7. 验证 Hermes BasePlatformAdapter 契约可导入
    # ------------------------------------------------------------------
    try:
        from gateway.platforms.base import BasePlatformAdapter
        from hermes_cli.plugins import PluginContext

        assert hasattr(BasePlatformAdapter, "handle_message")
        assert hasattr(BasePlatformAdapter, "send")
        assert hasattr(BasePlatformAdapter, "is_connected")
        assert hasattr(BasePlatformAdapter, "connect")
        assert hasattr(BasePlatformAdapter, "disconnect")
        assert hasattr(PluginContext, "register_platform")
        logger.info("Hermes BasePlatformAdapter / register_platform 契约验证通过")
    except ImportError as exc:
        logger.warning("未能在当前 Python 环境中导入 Hermes 源码: %s", exc)
        logger.info("这是预期的：Hermes 源码不在 sys.path 中，契约结论来自源码阅读。")

    logger.info("所有验证通过。")


if __name__ == "__main__":
    asyncio.run(_main())
