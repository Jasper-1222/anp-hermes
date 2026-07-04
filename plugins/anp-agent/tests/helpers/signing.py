"""共享测试辅助函数：生成 ANP DID WBA HTTP Signature 头。"""

from anp.authentication import DIDWbaAuthHeader


async def build_signed_headers(
    caller_identity: dict,
    target_url: str,
    body: str,
) -> dict[str, str]:
    """使用 DIDWbaAuthHeader 生成合法签名头。"""
    auth = DIDWbaAuthHeader(
        did_document_path=str(caller_identity["did_path"]),
        private_key_path=str(caller_identity["key_path"]),
        auth_mode="http_signatures",
    )
    headers = auth.get_auth_header(
        server_url=target_url,
        force_new=True,
        method="POST",
        headers={"Content-Type": "application/json"},
        body=body,
    )
    headers["Content-Type"] = "application/json"
    return headers
