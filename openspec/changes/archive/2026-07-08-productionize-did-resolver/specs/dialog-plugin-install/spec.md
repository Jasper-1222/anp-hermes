## MODIFIED Requirements

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