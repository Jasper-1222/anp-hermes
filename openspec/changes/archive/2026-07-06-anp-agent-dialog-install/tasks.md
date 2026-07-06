## 1. Documentation Update

- [x] 1.1 Update `plugins/anp-agent/README.md` with a "对话框安装" section
- [x] 1.2 Update `/home/peter/anp-hermes/CLAUDE.md` with the same install flow
- [x] 1.3 Include copy-pasteable message, expected LLM steps, and testbed onboarding hints

## 2. Verification

- [x] 2.1 Build or locate a plugin zip for `anp-agent`
- [x] 2.2 Send the documented install message in a local Hermes chat and verify the plugin is downloaded, installed, enabled, and the gateway restarts
- [x] 2.3 Run existing tests to ensure no regressions (`cd plugins/anp-agent && python -m pytest tests/ --cov=. --cov-fail-under=85 -q`)
- [x] 2.4 Run lint and format checks (`ruff check .`, `black --check .`)

## 3. Release / Distribution

- [x] 3.1 Decide final hosting location for the plugin zip
- [x] 3.2 Optionally add a build script that packages the plugin into a release zip
