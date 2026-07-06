## ADDED Requirements

### Requirement: Echo E2E test launches real Hermes with ANP plugin
The system SHALL provide an E2E test that starts a real Hermes gateway process with `anp-agent` loaded and an echo skill configured.

#### Scenario: Gateway starts and exposes ANP endpoints
- **WHEN** the echo E2E test fixture prepares a temporary `HERMES_HOME`, links `anp-agent` into `HERMES_HOME/plugins/anp-agent`, writes a config with the `anp` platform enabled, installs the `anp-echo` skill, copies the model/provider configuration from the user's real `~/.hermes/config.yaml`, and starts `hermes gateway run`
- **THEN** the gateway process remains alive, and `GET /agent/ad.json` returns HTTP 200 within 60 seconds

### Requirement: Echo E2E test returns the caller's message
The system SHALL verify that an ANP client can call the `chat` method through the running Hermes gateway and receive the original message back.

#### Scenario: Signed chat call returns echo response
- **WHEN** a valid ANP caller identity signs a `POST /agent/rpc` request with JSON-RPC method `chat` and params `{"message": "hello-e2e"}`
- **THEN** the server returns HTTP 200 with a JSON-RPC response whose `result.response` contains "hello-e2e" and contains no `error` field

### Requirement: E2E tests use an isolated Hermes home directory
The system SHALL isolate every E2E test run so that user-level Hermes configuration, skills, plugins, and memory are not modified.

#### Scenario: Temporary HERMES_HOME is fully isolated
- **WHEN** an E2E test fixture creates a temporary directory and sets `HERMES_HOME` to it
- **THEN** all Hermes state generated during the test lives under that directory, and the directory is deleted after the test

### Requirement: E2E tests are skipped by default
The system SHALL not run E2E tests unless the user explicitly opts in via a pytest command-line flag.

#### Scenario: Default pytest run skips E2E tests
- **WHEN** `pytest` runs without `--run-e2e`
- **THEN** all tests under `plugins/anp-agent/tests/e2e/` are skipped

#### Scenario: Explicit opt-in runs E2E tests
- **WHEN** `pytest` runs with `--run-e2e`
- **THEN** the E2E tests are collected and executed
