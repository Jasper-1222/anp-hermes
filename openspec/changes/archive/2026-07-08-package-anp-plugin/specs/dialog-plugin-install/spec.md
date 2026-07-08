## MODIFIED Requirements

### Requirement: README and CLAUDE.md document dialog-based plugin installation

The system SHALL document how to install the `anp-agent` plugin by sending a zip URL in the Hermes chat, without requiring any additional skill or code. The documentation SHALL describe the package-based release zip structure so the installer can verify that the extracted plugin root contains both Hermes plugin metadata and the `anp_agent` Python package.

#### Scenario: User reads installation docs

- **WHEN** a user opens `plugins/anp-agent/README.md` or `CLAUDE.md`
- **THEN** they SHALL find a "对话框安装" / "Dialog Install" section
- **AND** the section SHALL provide a copy-pasteable message like `安装插件 https://github.com/Jasper-1222/anp-hermes/releases/latest/download/anp-agent.zip`
- **AND** the section SHALL list the steps the LLM will perform:
  - Download the zip file
  - Inspect `plugin.yaml` and `__init__.py`
  - Confirm the package directory `anp_agent/` is present in the plugin root
  - Extract to `~/.hermes/plugins/anp-agent/`
  - Enable `anp-agent` in `~/.hermes/config.yaml`
  - Add or update the `gateway.platforms.anp` configuration
  - Restart the Hermes gateway
- **AND** the section SHALL report success or error to the user

#### Scenario: Installer validates package zip root

- **WHEN** the dialog installer or user inspects `anp-agent.zip`
- **THEN** the expected plugin root SHALL contain `plugin.yaml`, `__init__.py`, `README.md`, `pyproject.toml` and `anp_agent/`
- **AND** if the zip contains an extra top-level directory, the documentation SHALL instruct moving that directory's contents into `~/.hermes/plugins/anp-agent/` so `plugin.yaml` remains at the plugin root
