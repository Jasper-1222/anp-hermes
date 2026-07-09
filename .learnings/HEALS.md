## [HEAL-20260708-001] openspec_warning_cleanup

**Logged**: 2026-07-08T15:27:19+08:00
**Status**: verified
**Trigger**: tool-failure
**Active-Context**: OpenSpec sync/archive warning cleanup
**Area**: openspec
**Priority**: medium

### Failure
Two warnings remained after archiving `expose-hermes-tools`:

1. `openspec/changes/archive/2026-07-08-expose-hermes-tools/tasks.md` still had one incomplete checkbox:
   `- [ ] 6.7 通过 /opsx:verify expose-hermes-tools 后，同步 main specs 并归档。`
2. `openspec validate --all` failed because `openspec/specs/anp-auth-error-classification/spec.md` had a requirement text using `MAY` instead of the validator-required `SHALL` or `MUST` keyword:
   `requirements.5.text: Requirement must contain SHALL or MUST keyword`

### Diagnosis
The incomplete checkbox was a state-ordering issue: `expose-hermes-tools` had already been synced and archived, so invoking `/opsx:verify expose-hermes-tools` after archive failed because the active change no longer existed. The fix was to temporarily restore the archived change to active, run the OpenSpec artifact/task verification command, then mark task 6.7 complete and archive again.

The validation failure was a spec-format issue, not an implementation issue. OpenSpec validates each requirement body and requires `SHALL` or `MUST`; `anp-auth-error-classification` used `MAY` for `Challenge 头转发`. A matching main spec (`anp-platform-adapter`) already states this same behavior with `SHALL`, so the minimal consistent fix was to change that requirement sentence from `MAY` to `SHALL`.

### Fix
- Temporarily moved `openspec/changes/archive/2026-07-08-expose-hermes-tools` back to `openspec/changes/expose-hermes-tools` for verification.
- Changed `openspec/specs/anp-auth-error-classification/spec.md` requirement text from `MAY` to `SHALL` for challenge header forwarding.
- Marked task 6.7 complete in `openspec/changes/expose-hermes-tools/tasks.md` after verification.
- Moved the change back to `openspec/changes/archive/2026-07-08-expose-hermes-tools`.

### Verification
Ran:

```bash
openspec validate anp-auth-error-classification --type spec && \
openspec instructions apply --change "expose-hermes-tools" --json && \
openspec validate expose-hermes-tools --type change && \
openspec validate --all
```

Observed:

- `Specification 'anp-auth-error-classification' is valid`
- `progress.total: 31`, `progress.complete: 31`, `progress.remaining: 0`, `state: "all_done"`
- `Change 'expose-hermes-tools' is valid`
- `Totals: 15 passed, 0 failed (15 items)` while the change was active

Then re-archived and ran:

```bash
openspec list --json && openspec validate --all
```

Observed:

- Active changes list: `"changes": []`
- `Totals: 14 passed, 0 failed (14 items)`
- Archive path exists: `openspec/changes/archive/2026-07-08-expose-hermes-tools`

### Metadata
- Related Files: openspec/specs/anp-auth-error-classification/spec.md, openspec/changes/archive/2026-07-08-expose-hermes-tools/tasks.md
- See Also: none
- Pattern-Key: openspec.spec_validation
- Recurrence-Count: 1
- First-Seen / Last-Seen: 2026-07-08

---

## [HEAL-20260708-002] github_https_push_timeout

**Logged**: 2026-07-08T16:44:23+08:00
**Status**: verified
**Trigger**: external-change
**Active-Context**: ship push to master
**Area**: git/github
**Priority**: medium

### Failure
`git push origin master` failed while pushing the merged `master` branch:

```text
fatal: unable to access 'https://github.com/Jasper-1222/anp-hermes.git/': Failed to connect to github.com port 443 after 136905 ms: Couldn't connect to server
```

### Diagnosis
The repository state and verification gate were clean before pushing, so the failure was not caused by local git state. A direct WSL2 socket probe to `github.com:443` later succeeded, showing the issue was transient HTTPS connectivity to GitHub rather than a repository or credential problem.

### Fix
No project file patch was needed. Retried the push after confirming `github.com:443` connectivity:

```bash
python3 - <<'PY2'
import socket
s=socket.socket(); s.settimeout(20); s.connect(('github.com', 443)); s.close()
PY2
git push origin master
```

### Verification
The connectivity probe returned `connect ok`, and the retry returned:

```text
Everything up-to-date
```

This verified that the previous push had reached the remote or the remote had become synchronized by the time connectivity recovered.

### Metadata
- Related Files: none
- See Also: none
- Pattern-Key: external.github_https_timeout
- Recurrence-Count: 1
- First-Seen / Last-Seen: 2026-07-08

---

## [HEAL-20260708-003] subagent_context_overflow_retry

**Logged**: 2026-07-08T00:00:00+08:00
**Status**: verified
**Trigger**: tool-failure
**Active-Context**: brainstorming design planning for ANP client skill
**Area**: agent-orchestration
**Priority**: low

### Failure
A Plan subagent launched to design the ANP client skill terminated early with an API 502 and this error:

```text
API Error: 502 Your input exceeds the context window of this model. Please adjust your input and try again.
```

The failure blocked using the Plan agent output for the design phase.

### Diagnosis
The original subagent prompt included more context than the selected agent/model path could accept, despite the main session having a large context window. The task did not require all prior context verbatim; it only needed the settled product decisions and key reusable files.

### Fix
Relaunched the planning subagent with a shorter prompt, explicitly limited to the confirmed decisions and critical file references, and used a smaller model override for a concise planning pass.

### Verification
The replacement Plan subagent completed successfully and returned a usable implementation/design outline covering directory structure, script boundaries, command format, DID strategy, discovery/chat flow, error handling, and tests.

### Metadata
- Related Files: none
- See Also: none
- Pattern-Key: agent.context_window_overflow
- Recurrence-Count: 1
- First-Seen / Last-Seen: 2026-07-08

---

## [HEAL-20260709-001] regenerate_ignored_release_zip_for_packaging_tests

**Logged**: 2026-07-09T00:00:00+08:00
**Status**: verified
**Trigger**: tool-failure
**Active-Context**: subagent-driven-development baseline verification for add-anp-client-skill
**Area**: tests/packaging
**Priority**: medium

### Failure
Baseline verification in `plugins/anp-agent` failed:

```bash
python3 -m pytest tests/ -q
```

The suite reported `1 failed, 134 passed, 9 skipped`; the failing assertion was:

```text
tests/test_packaging.py::test_release_zip_contains_packaged_plugin_root_only
AssertionError: plugins/anp-agent/anp-agent.zip does not exist
```

### Diagnosis
`tests/test_packaging.py` intentionally validates the contents of `plugins/anp-agent/anp-agent.zip`, but `*.zip` is ignored by `.gitignore`, so a fresh git worktree created from tracked files does not contain this release artifact. The original checkout had an untracked `plugins/anp-agent/anp-agent.zip` with exactly the plugin root files (`plugin.yaml`, `__init__.py`, `README.md`, `pyproject.toml`, and `anp_agent/*.py`). This was an ignored artifact missing from the isolated worktree, not a source-code regression.

### Fix
Regenerated the ignored release artifact inside the worktree from tracked plugin files:

```bash
cd plugins/anp-agent
python3 - <<'PY'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path.cwd()
zip_path = root / 'anp-agent.zip'
include_files = [
    root / 'plugin.yaml',
    root / '__init__.py',
    root / 'README.md',
    root / 'pyproject.toml',
]
include_files.extend(sorted((root / 'anp_agent').rglob('*.py')))
with ZipFile(zip_path, 'w', compression=ZIP_DEFLATED) as archive:
    for path in include_files:
        archive.write(path, path.relative_to(root).as_posix())
print(zip_path)
PY
```

### Verification
Re-ran the original baseline command after regenerating the artifact:

```bash
cd plugins/anp-agent && python3 -m pytest tests/ -q
```

Observed:

```text
135 passed, 9 skipped in 5.77s
```

### Metadata
- Related Files: plugins/anp-agent/tests/test_packaging.py, plugins/anp-agent/anp-agent.zip, .gitignore
- See Also: none
- Pattern-Key: tests.ignored_release_artifact_missing
- Recurrence-Count: 1
- First-Seen / Last-Seen: 2026-07-09

---


## [HEAL-20260709-002] pytest_async_main_invocation

**Logged**: 2026-07-09T13:00:00+08:00
**Status**: verified
**Trigger**: tool-failure
**Active-Context**: Task 5 TDD GREEN phase
**Area**: tests/anp-client
**Priority**: low

### Failure

Task 5 chat helper 实现后，GREEN 命令失败：

```bash
python3 -m pytest clients/anp-client/tests/test_chat.py -q
```

观察到结果：

```text
1 failed, 13 passed
RuntimeError: asyncio.run() cannot be called from a running event loop
RuntimeWarning: coroutine '_cmd_chat' was never awaited
```

失败来自 `test_main_chat_reports_client_error_without_traceback`：该测试在 `@pytest.mark.asyncio` 测试函数里调用同步函数 `anp_client.main()`。

### Diagnosis

`anp_client.main()` 按设计是同步 CLI 入口，并通过 `asyncio.run(...)` 分发异步子命令。把调用 `main()` 的测试标记为 async 会让 pytest-asyncio 先创建一个正在运行的事件循环，导致 `asyncio.run()` 在真正测试 CLI 错误处理前失败。这是测试形态错误，不是生产 CLI 行为缺陷。

### Fix

移除 `test_main_chat_reports_client_error_without_traceback` 的 async marker 与 async 函数定义，将其保留为普通同步 pytest 测试；测试仍然用 async fake monkeypatch `chat_service`。

### Verification

重新运行原失败命令：

```bash
python3 -m pytest clients/anp-client/tests/test_chat.py -q
```

观察到：

```text
14 passed in 0.22s
```

随后重新运行请求的 client 测试集：

```bash
python3 -m pytest clients/anp-client/tests -q
```

观察到：

```text
75 passed in 3.04s
```

### Metadata
- Related Files: clients/anp-client/tests/test_chat.py
- See Also: none
- Pattern-Key: python.pytest_asyncio_run_in_running_loop
- Recurrence-Count: 1
- First-Seen / Last-Seen: 2026-07-09

---


## [HEAL-20260709-003] black_formatting_after_task5_edits

**Logged**: 2026-07-09T13:05:00+08:00
**Status**: verified
**Trigger**: tool-failure
**Active-Context**: Task 5 verify gate
**Area**: formatting/anp-client
**Priority**: low

### Failure

Task 5 实现后，格式检查失败：

```bash
python3 -m black --check clients/anp-client/scripts/anp_client.py clients/anp-client/scripts/signing.py clients/anp-client/tests/test_chat.py
```

观察到：

```text
would reformat clients/anp-client/tests/test_chat.py
would reformat clients/anp-client/scripts/anp_client.py
```

### Diagnosis

实现逻辑正确，但手工编辑的 chat 实现/测试中有若干行超过 Black 自动换行规则。Ruff 与空白检查均干净，因此这是纯格式化问题。

### Fix

对变更的 Python 文件运行 Black：

```bash
python3 -m black clients/anp-client/scripts/anp_client.py clients/anp-client/scripts/signing.py clients/anp-client/tests/test_chat.py
```

### Verification

重新运行原格式检查与请求的测试：

```bash
python3 -m black --check clients/anp-client/scripts/anp_client.py clients/anp-client/scripts/signing.py clients/anp-client/tests/test_chat.py
python3 -m pytest clients/anp-client/tests/test_chat.py -q
python3 -m pytest clients/anp-client/tests -q
```

观察到：

```text
3 files would be left unchanged.
14 passed in 0.22s
75 passed in 2.90s
```

### Metadata
- Related Files: clients/anp-client/scripts/anp_client.py, clients/anp-client/tests/test_chat.py
- See Also: none
- Pattern-Key: python.black_formatting_required
- Recurrence-Count: 1
- First-Seen / Last-Seen: 2026-07-09

---
