## 1. Documentation Update

- [ ] 1.1 Update `plugins/anp-agent/README.md` with a "对话框安装" section
- [ ] 1.2 Update `/home/peter/anp-hermes/CLAUDE.md` with the same install flow
- [ ] 1.3 Include copy-pasteable message, expected LLM steps, and testbed onboarding hints

## 2. Verification

- [ ] 2.1 Build or locate a plugin zip for `anp-agent`
- [ ] 2.2 Send the documented install message in a local Hermes chat and verify the plugin is downloaded, installed, enabled, and the gateway restarts
- [ ] 2.3 Run existing tests to ensure no regressions (`pytest tests/ --cov=. --cov-fail-under=85`)
- [ ] 2.4 Run lint and format checks (`ruff check .`, `black --check .`)

## 3. Release / Distribution

- [ ] 3.1 Decide final hosting location for the plugin zip
- [ ] 3.2 Optionally add a build script that packages the plugin into a release zip
