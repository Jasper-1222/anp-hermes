"""ANP 插件服务端认证模块。

本模块使用 ANP SDK 的 DidWbaVerifier 验证调用方 DID WBA HTTP Message Signature，
并返回调用方 DID。
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import aiohttp
from anp.authentication import did_wba_verifier as did_wba_verifier_module
from anp.authentication.did_wba_verifier import (
    DidWbaVerifier,
    DidWbaVerifierConfig,
    DidWbaVerifierError,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from identity import ANPIdentity, _atomic_write_text

logger = logging.getLogger(__name__)

# DID 文档解析默认超时（秒）
_DEFAULT_DID_RESOLVE_TIMEOUT = 10

# DID 文档解析 base URL 环境变量名
_DID_RESOLVER_BASE_URL_ENV = "ANP_DID_RESOLVER_BASE_URL"

# 保存模块原始 resolver，避免多个 ANPAuth 实例反复嵌套包装
_ORIGINAL_RESOLVER = getattr(did_wba_verifier_module, "resolve_did_wba_document", None)

# JWT 密钥文件名
_JWT_PRIVATE_KEY_NAME = "jwt_private_key.pem"
_JWT_PUBLIC_KEY_NAME = "jwt_public_key.pem"

# 密钥文件权限
_PRIVATE_KEY_MODE = 0o600
_PUBLIC_KEY_MODE = 0o644


class AuthenticationError(Exception):
    """认证失败时抛出的结构化异常。

    携带 HTTP 状态码、JSON-RPC 错误码与可选 challenge 头，
    供 server.py 直接构造对外响应，无需反向解析原始异常。
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 401,
        rpc_code: int = -32001,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.rpc_code = rpc_code
        self.headers = headers


# 当前生效的 wrapper 配置；后创建的实例覆盖前一个
_resolver_config = {"timeout": _DEFAULT_DID_RESOLVE_TIMEOUT, "base_url": None}


def _classify_verifier_error(exc: DidWbaVerifierError) -> tuple[str, int, int]:
    """根据 DidWbaVerifierError 消息与状态码分类认证失败。

    Returns:
        (对外消息, HTTP 状态码, JSON-RPC 错误码)
    """
    message = (exc.args[0] if exc.args else "").lower()

    # DID 文档解析失败：超时、网络错误、HTTPS 解析失败
    if "resolve did" in message or ("did document" in message and "timeout" in message):
        return "DID 文档无法解析", 401, -32002

    # 缺少认证头
    if "missing" in message and any(
        keyword in message
        for keyword in ("signature", "authorization", "signature-input", "authentication")
    ):
        return "缺少认证头", 401, -32003

    # DID 文档无效：proof / binding / 结构校验失败
    if any(keyword in message for keyword in ("invalid did document", "proof", "binding")):
        return "DID 文档无效", 401, -32004

    # 认证方法未授权
    if "verification method" in message or "not in authentication" in message:
        return "认证方法未授权", 403, -32005

    # 默认：签名相关错误
    return "DID WBA 签名无效", 401, -32001


def _make_resolver_wrapper(resolve_fn):
    """创建支持超时与 base URL 覆盖的 resolver wrapper。

    Wrapper 上的 ``_anp_auth_wrapper`` 标记用于避免多个 ``ANPAuth`` 实例嵌套包装。
    """
    from anp.authentication.did_resolver import resolve_did_document

    async def _resolver_wrapper(did: str, verify_proof: bool = False):
        timeout = _resolver_config["timeout"]
        base_url = _resolver_config["base_url"]
        try:
            if base_url is not None:
                coro = resolve_did_document(
                    did,
                    verify_proof=verify_proof,
                    base_url_override=base_url,
                    verify_ssl=False,
                )
            else:
                coro = resolve_fn(did, verify_proof=verify_proof)
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise DidWbaVerifierError(
                "Failed to resolve DID document: timeout",
                status_code=401,
            ) from exc
        except aiohttp.ClientError as exc:
            raise DidWbaVerifierError(
                f"Failed to resolve DID document: {exc.__class__.__name__}",
                status_code=401,
            ) from exc

    _resolver_wrapper._anp_auth_wrapper = True  # noqa: SLF001
    return _resolver_wrapper


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
        self._did_resolve_timeout = _parse_timeout(
            os.environ.get("ANP_DID_RESOLVE_TIMEOUT", _DEFAULT_DID_RESOLVE_TIMEOUT)
        )
        self._did_resolver_base_url = os.environ.get(_DID_RESOLVER_BASE_URL_ENV)
        self._patch_resolver()

    def _patch_resolver(self) -> None:
        """包装 DID 文档解析函数，支持超时与 base URL 覆盖。

        ANP SDK 的 `resolve_did_wba_document` 默认通过 HTTPS 解析 DID 文档，
        且不暴露自定义 resolver 接口。这里通过模块级 monkeypatch 支持：

        - `ANP_DID_RESOLVE_TIMEOUT`：自定义解析超时。
        - `ANP_DID_RESOLVER_BASE_URL`：覆盖 DID 文档 base URL（用于测试）。

        .. note::
            同一进程内后创建的 ``ANPAuth`` 实例会覆盖全局 wrapper 配置，因此不要
            在同一进程内同时运行需要不同超时/base_url 的 ``ANPAuth`` 实例。
        """
        _resolver_config["timeout"] = self._did_resolve_timeout
        _resolver_config["base_url"] = self._did_resolver_base_url

        current = did_wba_verifier_module.resolve_did_wba_document
        if getattr(current, "_anp_auth_wrapper", False):
            # 已经是 wrapper，只需更新全局配置
            logger.debug(
                "DID resolver wrapper 已存在，更新配置: timeout=%.1f, base_url=%s",
                self._did_resolve_timeout,
                self._did_resolver_base_url if self._did_resolver_base_url else "(none)",
            )
            return

        wrapper = _make_resolver_wrapper(current)
        did_wba_verifier_module.resolve_did_wba_document = wrapper
        logger.debug(
            "DID 文档解析超时已设置为 %.1f 秒，base_url_override=%s",
            self._did_resolve_timeout,
            self._did_resolver_base_url if self._did_resolver_base_url else "(none)",
        )

    def _patch_resolver_with_timeout(self) -> None:
        """保留旧方法名作为兼容别名，实际调用 ``_patch_resolver``。"""
        self._patch_resolver()

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
            AuthenticationError: 结构化认证失败异常，携带 status_code、rpc_code、headers。
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
                raise AuthenticationError(
                    "DID WBA 签名无效",
                    status_code=401,
                    rpc_code=-32001,
                )
            return caller_did
        except DidWbaVerifierError as exc:
            logger.warning("DID WBA 认证失败: %s", exc)
            message, status_code, rpc_code = _classify_verifier_error(exc)
            raise AuthenticationError(
                message,
                status_code=status_code,
                rpc_code=rpc_code,
                headers=exc.headers,
            ) from exc
        except asyncio.TimeoutError as exc:
            logger.warning("DID 文档解析超时: %s", exc)
            raise AuthenticationError(
                "DID 文档无法解析",
                status_code=401,
                rpc_code=-32002,
            ) from exc
        except aiohttp.ClientError as exc:
            logger.warning("DID 文档解析网络错误: %s", exc)
            raise AuthenticationError(
                "DID 文档无法解析",
                status_code=401,
                rpc_code=-32002,
            ) from exc
        except AuthenticationError:
            raise
        except Exception as exc:
            logger.exception("认证过程中发生未预期异常")
            raise AuthenticationError(
                "认证服务内部错误",
                status_code=500,
                rpc_code=-32006,
            ) from exc


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


def _save_key(path: Path, pem: str, *, is_private: bool) -> None:
    """保存密钥 PEM 文件，私钥 0o600，公钥 0o644。

    复用 identity._atomic_write_text，在创建时即应用权限，避免 write->chmod 竞态。
    """
    mode = _PRIVATE_KEY_MODE if is_private else _PUBLIC_KEY_MODE
    _atomic_write_text(path, pem, mode)


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
    _save_key(private_path, private_pem, is_private=True)
    _save_key(public_path, public_pem, is_private=False)
    return private_pem, public_pem


def _parse_timeout(raw: Any) -> float:
    """解析 DID 解析超时配置，非法值回退默认值。"""
    try:
        return float(raw)
    except (ValueError, TypeError):
        logger.warning(
            "ANP_DID_RESOLVE_TIMEOUT 值无效 (%r)，回退默认值 %s",
            raw,
            _DEFAULT_DID_RESOLVE_TIMEOUT,
        )
        return float(_DEFAULT_DID_RESOLVE_TIMEOUT)


def create_auth(identity: ANPIdentity) -> ANPAuth:
    """工厂函数：根据服务端身份创建 ANPAuth 实例。"""
    return ANPAuth(identity)
