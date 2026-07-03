"""ANP 插件服务端认证模块。

本模块使用 ANP SDK 的 DidWbaVerifier 验证调用方 DID WBA HTTP Message Signature，
并返回调用方 DID。
"""

import logging
from pathlib import Path

from anp.authentication.did_wba_verifier import (
    DidWbaVerifier,
    DidWbaVerifierConfig,
    DidWbaVerifierError,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from identity import ANPIdentity

logger = logging.getLogger(__name__)

# JWT 密钥文件名
_JWT_PRIVATE_KEY_NAME = "jwt_private_key.pem"
_JWT_PUBLIC_KEY_NAME = "jwt_public_key.pem"


class AuthenticationError(Exception):
    """认证失败时抛出的通用异常，不包含内部详细原因。"""


class ANPAuth:
    """服务端 DID WBA 认证器。

    初始化时加载或生成 RSA 密钥对，用于 DidWbaVerifier 签发 access token。
    """

    def __init__(self, identity: ANPIdentity) -> None:
        """构造认证器。

        Args:
            identity: 服务端自身的 ANP DID 身份，其中的 data_dir 用于存放 JWT 密钥。
        """
        self._identity = identity
        private_key_pem, public_key_pem = _load_or_generate_jwt_keys(identity.data_dir)
        config = DidWbaVerifierConfig(
            jwt_private_key=private_key_pem,
            jwt_public_key=public_key_pem,
            jwt_algorithm="RS256",
            access_token_expire_minutes=60,
            allow_http_signatures=True,
            allow_legacy_didwba=False,
            emit_authentication_info_header=True,
            emit_legacy_authorization_header=False,
            require_nonce_for_http_signatures=True,
        )
        self._verifier = DidWbaVerifier(config)

    async def authenticate(
        self,
        method: str,
        url: str,
        headers: dict,
        body: str | bytes | None = None,
    ) -> str:
        """验证 HTTP 请求签名并返回调用方 DID。

        Args:
            method: HTTP 方法，如 "POST"。
            url: 请求完整 URL。
            headers: 请求头字典，需包含 Signature-Input / Signature。
            body: 请求体，可选。

        Returns:
            调用方 DID 字符串。

        Raises:
            AuthenticationError: 任何认证失败场景均抛出此异常，具体原因写入日志。
        """
        try:
            result = await self._verifier.verify_request(
                method=method,
                url=url,
                headers=headers,
                body=body,
            )
            caller_did = result.get("did")
            if not isinstance(caller_did, str):
                logger.error("DidWbaVerifier 返回结果缺少 did 字段: %s", result)
                raise AuthenticationError("认证失败")
            return caller_did
        except DidWbaVerifierError as exc:
            logger.warning("DID WBA 认证失败: %s", exc)
            raise AuthenticationError("认证失败") from exc
        except Exception as exc:
            logger.exception("认证过程中发生未预期异常")
            raise AuthenticationError("认证失败") from exc


def _generate_rsa_key_pair() -> tuple[str, str]:
    """生成 RSA 密钥对，以 PEM 字符串形式返回 (private, public)。"""
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


def _save_key(path: Path, pem: str) -> None:
    """保存密钥 PEM 文件，私钥权限 0o600，公钥 0o644。"""
    path.write_text(pem, encoding="utf-8")
    if "PRIVATE" in path.name:
        path.chmod(0o600)
    else:
        path.chmod(0o644)


def _load_or_generate_jwt_keys(data_dir: Path) -> tuple[str, str]:
    """加载或生成 JWT 签名/验签密钥对。

    密钥持久化在 data_dir 下的 jwt_private_key.pem 和 jwt_public_key.pem。
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    private_path = data_dir / _JWT_PRIVATE_KEY_NAME
    public_path = data_dir / _JWT_PUBLIC_KEY_NAME

    if private_path.exists() and public_path.exists():
        private_pem = private_path.read_text(encoding="utf-8")
        public_pem = public_path.read_text(encoding="utf-8")
        return private_pem, public_pem

    private_pem, public_pem = _generate_rsa_key_pair()
    _save_key(private_path, private_pem)
    _save_key(public_path, public_pem)
    return private_pem, public_pem


def create_auth(identity: ANPIdentity) -> ANPAuth:
    """工厂函数：根据服务端身份创建 ANPAuth 实例。"""
    return ANPAuth(identity)
