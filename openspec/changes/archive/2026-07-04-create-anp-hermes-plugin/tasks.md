## 1. 项目骨架与依赖

- [x] 1.1 创建插件目录 `plugins/anp-agent/`，包含 `plugin.yaml`、`adapter.py`、`pyproject.toml`
- [x] 1.2 在 `pyproject.toml` 中添加依赖：核心插件使用 `anp>=0.8.8,<0.9.0` 和 `aiohttp`；测试客户端使用 `anp[api]`
- [x] 1.3 配置插件元数据（名称、版本、作者、所需环境变量，包括 `ANP_ALLOW_ALL_USERS`）

## 2. DID WBA 身份管理

- [x] 2.1 实现 `identity.py`：检测本地是否已有 DID 文档和私钥
- [x] 2.2 实现首次启动时调用 `anp.authentication.create_did_wba_document` 生成身份
- [x] 2.3 将 DID 文档、私钥 PEM、`agent.json` 持久化到 `~/.hermes/plugins/anp-agent/`，私钥文件权限 `0o600`
- [x] 2.4 为 identity 模块编写单元测试

## 3. Hermes 平台适配器

- [x] 3.1 实现 `ANPAdapter` 类，继承 `BasePlatformAdapter`
- [x] 3.2 实现配置解析：支持 `config.yaml` extra 字段和 `ANP_HOST` / `ANP_PORT` / `ANP_DATA_DIR` 环境变量
- [x] 3.3 实现 `connect()`：加载/生成身份，启动 aiohttp 服务器，调用 `_mark_connected()`
- [x] 3.4 实现 `disconnect()`：停止 aiohttp 服务器，取消并清理所有 pending futures，调用 `_mark_disconnected()`
- [x] 3.5 实现 `send()`：识别 `anp:` 前缀的 `chat_id`，设置对应 Future 结果
- [x] 3.6 实现 Future TTL 清理：为 pending futures 设置过期时间，防止内存泄漏
- [x] 3.7 实现 `register(ctx)` 入口，向 Hermes `platform_registry` 注册 `anp` 平台
- [x] 3.8 为适配器生命周期编写单元测试（mock BasePlatformAdapter 依赖）

## 4. ANP HTTP 端点

- [x] 4.1 实现 `GET /agent/ad.json`，返回 Agent Description JSON
- [x] 4.2 实现 `GET /agent/interface.json`，返回 OpenRPC 文档（至少包含 `chat` 方法）
- [x] 4.3 实现 `POST /agent/rpc`：解析 JSON-RPC 请求，验证 DID WBA 签名
- [x] 4.4 实现请求-响应桥接：创建 Future、构造 `MessageEvent`、调用 `handle_message`、等待 Future、返回 JSON-RPC 响应
- [x] 4.5 实现超时处理：配置项 `request_timeout`，超时时返回 JSON-RPC error
- [x] 4.6 为 HTTP 端点编写单元测试，覆盖合法请求、非法签名、超时场景

## 5. 端到端测试

- [x] 5.1 编写测试脚本，启动插件内置 aiohttp 服务器（不依赖完整 Hermes gateway）
- [x] 5.2 使用 ANP SDK 的 `RemoteAgent.discover()` 发现服务并调用 `chat`
- [x] 5.3 验证非法签名请求被拒绝
- [x] 5.4 编写文档说明如何运行端到端测试

## 6. 文档与代码质量

- [x] 6.1 编写 `plugins/anp-agent/README.md`：安装、配置、测试说明
- [x] 6.2 配置代码格式化与 lint（ruff / black），并在 CI 中运行
- [x] 6.3 确保单元测试覆盖率不低于 85%
- [x] 6.4 更新项目根目录 `CLAUDE.md`，补充 ANP 插件相关开发命令和架构说明

## 7. 后续待办（不实现）

- [ ] 7.1 调研 AP2 支付协议集成方案（Deferred）
- [ ] 7.2 调研 E2EE 加密集成方案（Deferred）
