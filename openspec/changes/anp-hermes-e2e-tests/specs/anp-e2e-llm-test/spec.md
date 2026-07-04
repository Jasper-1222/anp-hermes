## ADDED Requirements

### Requirement: LLM E2E test runs single-turn chat through Hermes
The system SHALL provide an E2E test that starts a real Hermes gateway with a configured LLM provider and verifies a single-turn `chat` call returns a non-empty, valid response.

#### Scenario: Single-turn chat returns valid response
- **WHEN** the LLM E2E test fixture starts `hermes gateway run` with a temporary `HERMES_HOME` configured for a real LLM provider (copied from the user's real `~/.hermes/config.yaml`) and `anp-agent` enabled
- **AND** a valid ANP caller signs and sends `POST /agent/rpc` with method `chat` and params `{"message": "你好"}`
- **THEN** the server returns HTTP 200 with a JSON-RPC result containing a non-empty `response` string and no `error` field

### Requirement: LLM E2E test verifies multi-turn context retention
The system SHALL verify that Hermes retains conversation context across multiple sequential `chat` calls from the same caller DID.

#### Scenario: Multi-turn chat references prior user input
- **WHEN** the caller sends a first `chat` call with `{"message": "我叫 Alice"}` and receives a response
- **AND** the caller sends a second `chat` call with `{"message": "我叫什么名字？"}` using the same caller DID
- **THEN** the second response contains "Alice" or a clear semantic acknowledgement of the name

### Requirement: LLM E2E tests are gated behind slow-test markers
The system SHALL classify LLM-based E2E tests as slow and require an additional flag to run them.

#### Scenario: Default E2E run skips LLM tests
- **WHEN** `pytest` runs with `--run-e2e` but without `--run-slow-e2e`
- **THEN** LLM E2E tests are skipped

#### Scenario: Full E2E run includes LLM tests
- **WHEN** `pytest` runs with both `--run-e2e` and `--run-slow-e2e` and the required LLM provider credentials are available
- **THEN** LLM E2E tests are executed

### Requirement: LLM E2E tests use loose assertions
The system SHALL use non-deterministic assertions for LLM responses to avoid flaky failures caused by model output variation.

#### Scenario: Response assertion tolerates model variation
- **WHEN** an LLM E2E test receives a chat response
- **THEN** the test asserts only that the response is non-empty, is valid JSON-RPC, and satisfies the scenario-specific semantic condition (e.g., contains a keyword or answers the question topically)
