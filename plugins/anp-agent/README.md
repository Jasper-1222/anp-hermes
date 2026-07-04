# Hermes ANP Agent 平台插件

ANP（Agent Network Protocol）服务智能体 Hermes 平台插件参考实现。

## 功能

- 为 Hermes 生成并管理 ANP 原生 DID WBA 身份（`did:wba:`）。
- 暴露标准 ANP 端点：
  - `GET /agent/ad.json`：Agent Description
  - `GET /agent/interface.json`：OpenRPC 接口文档
  - `POST /agent/rpc`：JSON-RPC 2.0 调用入口
- 使用 DID WBA HTTP Message Signatures 验证调用方身份。
- 通过 asyncio Future 将 ANP 请求桥接到 Hermes 消息处理流程。

## 安装

```bash
pip install -e plugins/anp-agent/
```

或将 `plugins/anp-agent/` 复制到 `~/.hermes/plugins/anp-agent/`。

## 配置

在 `~/.hermes/config.yaml` 中启用 `anp` 平台：

```yaml
gateway:
  platforms:
    anp:
      extra:
        host: 0.0.0.0
        port: 8900
        hostname: localhost
        endpoint: http://localhost:8900
        data_dir: ~/.hermes/plugins/anp-agent/
        request_timeout: 60
        future_ttl: 120
```

环境变量优先级高于配置文件：

- `ANP_HOST`
- `ANP_PORT`
- `ANP_HOSTNAME`
- `ANP_ENDPOINT`
- `ANP_DATA_DIR`
- `ANP_REQUEST_TIMEOUT`
- `ANP_FUTURE_TTL`
- `ANP_ALLOW_ALL_USERS`（测试环境必需）

## 测试

```bash
cd plugins/anp-agent
python -m pytest tests/ -v
```

## 注意事项

- 测试环境必须设置 `ANP_ALLOW_ALL_USERS=1`，否则 Hermes allowlist 会拒绝新平台。
- 本期仅实现身份认证与明文 JSON-RPC 调用，不实现 AP2 支付与 E2EE 加密。
- DID 文档需要在生产环境真实可解析，测试时插件会公开自己的 DID 文档。

## 许可证

MIT
