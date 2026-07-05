## ADDED Requirements

### Requirement: README and CLAUDE.md document dialog-based plugin installation

The system SHALL document how to install the `anp-agent` plugin by sending a zip URL in the Hermes chat, without requiring any additional skill or code.

#### Scenario: User reads installation docs

- **WHEN** a user opens `plugins/anp-agent/README.md` or `/home/peter/anp-hermes/CLAUDE.md`
- **THEN** they SHALL find a "对话框安装" / "Dialog Install" section
- **AND** the section SHALL provide a copy-pasteable message like `安装插件 https://host/downloads/anp-agent.zip`
- **AND** the section SHALL list the steps the LLM will perform:
  - Download the zip file
  - Inspect `plugin.yaml` and `__init__.py`
  - Extract to `~/.hermes/plugins/anp-agent/`
  - Enable `anp-agent` in `~/.hermes/config.yaml`
  - Add or update the `gateway.platforms.anp` configuration
  - Restart the Hermes gateway
- **AND** the section SHALL report success or error to the user

### Requirement: Documentation includes testbed onboarding hints

The system SHALL include post-install guidance in the same documentation so the LLM or user can connect the plugin to the ANP testbed.

#### Scenario: Plugin installed via dialog

- **WHEN** the plugin has been installed and the gateway has restarted
- **THEN** the documentation SHALL explain the remaining steps:
  - Set `ANP_ALLOW_ALL_USERS=1` for testing environments
  - Start or configure a DID document resolver (e.g., `ANP_DID_RESOLVER_BASE_URL`)
  - Configure the LLM provider in `~/.hermes/config.yaml` if not already present
- **AND** the documentation SHALL mention that these can also be triggered by asking the LLM in the same chat

### Requirement: No new artifacts beyond documentation

The system SHALL NOT create any new skill, script, or code file to support the dialog install flow.

#### Scenario: Inspecting the repository for install helpers

- **WHEN** a contributor searches the repository for install-related files
- **THEN** they SHALL find only updated documentation
- **AND** they SHALL NOT find any new skill directory, install script, or Hermes core modification
