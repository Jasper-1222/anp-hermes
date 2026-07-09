"""ANP DID WBA HTTP Signature 生成。"""

from __future__ import annotations

from anp.authentication import DIDWbaAuthHeader

from did_identity import CallerIdentity


async def build_signed_headers(
    identity: CallerIdentity,
    target_url: str,
    body: str,
) -> dict[str, str]:
    """为 JSON-RPC POST body 生成 DID WBA HTTP Signature 请求头。"""
    auth = DIDWbaAuthHeader(
        did_document_path=str(identity.did_path),
        private_key_path=str(identity.key_path),
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
