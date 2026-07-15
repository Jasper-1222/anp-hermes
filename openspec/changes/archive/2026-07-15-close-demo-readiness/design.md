## Context

当前默认分支为 `master`，CI 却监听 `main`；打包脚本只生成版本化文件，而插件 README 使用稳定下载名；插件包测试要求 ignored zip 预先存在；仓库声明 MIT 但没有 LICENSE。项目已有完整本地测试体系，因此只需收敛这些工程与文档边界，不需要生产级扩展。

## Goals / Non-Goals

**Goals:**

- 让 Python 3.12 CI 在 `master` push/PR 上运行 OpenSpec、根级、客户端和插件门禁。
- 让普通测试不依赖固定端口或预生成 ignored zip。
- 让一次打包生成版本化 plugin/client zip 和稳定别名，并包含 MIT LICENSE。
- 让主要文档和 main specs 反映当前技术 Demo 状态。

**Non-Goals:**

- 不创建 tag、Release、PR 或远端推送。
- 不增加生产部署、Bearer 扩展、限流、持久化审计、resolver 上游改造、跨机器 DID、AP2 或 E2EE。
- 不提高覆盖率阈值，不维护多 Python 版本矩阵。

## Decisions

1. CI 固定 Python 3.12，降低技术 Demo 维护成本。
2. 发布脚本返回四个路径；稳定别名是版本化文件的字节级副本。
3. 根 LICENSE 作为 `LICENSE` 归档到 plugin/client zip。
4. 插件包测试直接调用根打包脚本并使用 `tmp_path`，不写仓库 ignored 产物。
5. adapter 测试通过 fixture 显式传入 `port=0`，不停止用户正在运行的 Hermes。
6. OpenSpec 只使用一个 change；P2 只记录为非目标。

## Risks / Trade-offs

- 单版本 CI 不证明 Python 3.10/3.11 兼容；技术 Demo 接受此取舍。
- 本轮不创建 Release，稳定 URL 只是后续发布约定；文档必须用条件式表述。
- 真正的 GitHub Actions 结果要在未来推送后才能观察；本轮以本地命令和 workflow 内容校验为准。
