## MODIFIED Requirements

### Requirement: Echo E2E test launches real Hermes with ANP plugin
The system SHALL provide an E2E test that starts a real Hermes gateway process with `anp-agent` loaded, an echo skill configured, a temporary Hermes home, a temporary process `HOME`, and a deterministic mock LLM provider config that does not read or require the user's real `~/.hermes/config.yaml`.

#### Scenario: Gateway starts and exposes ANP endpoints
- **WHEN** the echo E2E test fixture prepares a temporary `HOME`, a temporary `HERMES_HOME`, links `anp-agent` into `HERMES_HOME/plugins/anp-agent`, writes a minimal config with the `anp` platform enabled, configures the local mock LLM provider, installs the `anp-echo` skill, and starts `hermes gateway run`
- **THEN** the gateway process remains alive, and `GET /agent/ad.json` returns HTTP 200 within 60 seconds

#### Scenario: Echo E2E does not require user Hermes config
- **WHEN** the user's real `~/.hermes/config.yaml` is absent, unreadable, or contains unrelated provider settings
- **THEN** the echo E2E fixture still uses its generated temporary config and does not skip or fail because of the user config

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

#### Scenario: Temporary HOME prevents accidental user config access
- **WHEN** the echo E2E gateway process runs
- **THEN** its `HOME` points at a temporary directory, so implicit `~/.hermes` lookups cannot read or write the user's real Hermes home

### Requirement: E2E tests are skipped by default
The system SHALL not run E2E tests unless the user explicitly opts in via a pytest command-line flag.

#### Scenario: Default pytest run skips E2E tests
- **WHEN** `pytest` runs without `--run-e2e`
- **THEN** all tests under `plugins/anp-agent/tests/e2e/` are skipped

#### Scenario: Explicit opt-in runs E2E tests
- **WHEN** `pytest` runs with `--run-e2e`
- **THEN** the E2E tests are collected and executed