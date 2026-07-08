# dialog-plugin-install Specification

## Purpose

定义 `anp-agent` 插件通过 Hermes 对话框进行安装、启用与测试床接入的文档要求。

## Requirements

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

### Requirement: Documentation includes testbed onboarding hints

The system SHALL include post-install guidance in the same documentation so the LLM or user can connect the plugin to the ANP testbed. The documentation SHALL clearly distinguish local testbed resolver override from production DID WBA resolution: `ANP_DID_RESOLVER_BASE_URL` is only for loopback local development/testing, while production deployments SHALL publish DID Documents at the standard DID WBA HTTPS path for the service DID.

#### Scenario: Plugin installed via dialog

- **WHEN** the plugin has been installed and the gateway has restarted
- **THEN** the documentation SHALL explain the remaining steps:
  - Set `ANP_ALLOW_ALL_USERS=1` for testing environments
  - Start or configure a local loopback DID document resolver for testbed use (e.g., `ANP_DID_RESOLVER_BASE_URL=http://localhost:<port>`)
  - Configure the LLM provider in `~/.hermes/config.yaml` if not already present
- **AND** the documentation SHALL mention that these can also be triggered by asking the LLM in the same chat
- **AND** the documentation SHALL state that production deployments should not rely on `ANP_DID_RESOLVER_BASE_URL`, but should make the DID Document resolvable through the DID WBA default HTTPS path

### Requirement: No new artifacts beyond documentation

The system SHALL NOT create any new skill, script, or code file to support the dialog install flow.

#### Scenario: Inspecting the repository for install helpers

- **WHEN** a contributor searches the repository for install-related files
- **THEN** they SHALL find only updated documentation
- **AND** they SHALL NOT find any new skill directory, install script, or Hermes core modification
