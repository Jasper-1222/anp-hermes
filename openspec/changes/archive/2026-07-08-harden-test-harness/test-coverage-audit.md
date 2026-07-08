# harden-test-harness 测试覆盖盘点

## 已覆盖场景

- JSON-RPC invalid request：`tests/test_server.py` 已覆盖 parse error、invalid `jsonrpc`、batch、notification/缺失 id、空/数字 id、缺少 method；需补非字符串 method 与非对象 params。
- Bridge 内部错误：`tests/test_bridge.py` 已覆盖 timeout、stop 取消 pending、handler exception、pending capacity exhausted；`tests/test_server.py` 已覆盖 bridge error 映射为 JSON-RPC `-32603`。
- 并发 request id 隔离：`tests/test_bridge.py` 已覆盖相同客户端 JSON-RPC id 并发分配不同内部 request id 且响应不串扰。
- Core Binding：`tests/test_server.py` 已覆盖 `params.body.message`、body 优先级、invalid envelope shape、unsupported profile、unsupported security profile。
- `anp.get_capabilities`：`tests/test_server.py` 已覆盖返回 service DID、profiles、security profiles、limits、content types 且不调用 bridge。
- `Authentication-Info`：`tests/test_auth.py` 已覆盖 verifier 成功头过滤和无头返回空 headers；`tests/test_server.py` 已覆盖成功 JSON-RPC 响应透传 `Authentication-Info` 且错误响应不透传成功头。
- 身份与配置：`tests/test_config.py` 已覆盖默认 data_dir、显式配置与 `ANP_DATA_DIR` 优先级；`tests/test_identity.py` 已覆盖首次生成、已有身份加载、私钥 `0o600`、显式 `~` 目录、损坏 DID 文档备份、缺失私钥重新生成和 hostname 变化。
- 公开发现与能力文档：`tests/test_server.py` 已覆盖 `/agent/ad.json`、`/.well-known/agent-descriptions`、`/agent/interface.json` 与 `anp.get_capabilities`。
- E2E 默认 gating：`tests/e2e/conftest.py` 已在未传 `--run-e2e` 时跳过 E2E 目录。

## 需要补齐或调整的场景

- coverage omit 需要排除 `tests/*.py`、`__pycache__/*` 与运行态 DID/PEM 文件。
- Echo E2E fixture 需要证明并实现不读取用户真实 `~/.hermes/config.yaml`，且子进程设置临时 `HOME` / `HERMES_HOME`。
- LLM E2E 需要证明并实现未传 `--run-slow-e2e` 或缺少 API key 时在启动 gateway 前 skip。
- JSON-RPC invalid request 需补非字符串 method 与非对象 params 的 HTTP 400 / `-32600` 测试。
- 身份损坏场景需补“私钥内容损坏时备份旧私钥并重新生成”的测试。
