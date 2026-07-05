## Context

`anp-agent` is a Hermes platform plugin. Today it is installed via `pip install -e .` or by manually symlinking the source into `~/.hermes/plugins/`. IOAT has demonstrated that a plugin can be installed by simply pasting a zip URL into the Hermes chat, where the LLM performs the download, extraction, configuration, and gateway restart without any additional skill. We want the same experience for `anp-agent` while keeping the implementation minimal and zero-intrusive to Hermes core.

## Goals / Non-Goals

**Goals:**

- Enable dialog-based installation of `anp-agent` from a zip URL.
- Document the exact prompt and steps so any capable LLM in Hermes can reproduce the flow.
- Guide the user to connect the installed plugin to the ANP testbed.
- Avoid any new code files, skills, or changes to Hermes core.

**Non-Goals:**

- Implementing a native Hermes plugin installer.
- Creating a Hermes skill or helper script.
- Supporting non-zip formats (e.g., tar, git URL) from the dialog.
- Automatic testbed registration or DID generation.

## Decisions

1. **Use documentation prompts instead of a skill or core change.**
   - The latest evidence shows that Hermes LLM can already perform the install autonomously when given a clear message. Adding a skill would introduce an extra installation step and contradict the "simple is beautiful" principle.
   - Alternative considered: create `anp-agent-install` skill. Rejected because it adds a new artifact and an extra installation step.

2. **Document the exact user message and expected LLM actions.**
   - README/CLAUDE.md will contain a copy-pasteable message like `安装插件 https://host/anp-agent.zip`.
   - It will also list the LLM steps so users understand and can verify what happens.

3. **Post-install testbed guidance is included in the same documentation.**
   - After the plugin loads, the user needs to set `ANP_ALLOW_ALL_USERS` and configure DID resolution. Keeping this in the same doc reduces context switching.

## Risks / Trade-offs

- **[Risk] Not all Hermes LLM configurations may reliably execute multi-step shell operations.** → Mitigation: keep the documented steps explicit and simple; advanced users can still use manual install.
- **[Risk] Zip contents may vary or be malformed.** → Mitigation: documentation instructs the LLM to verify `plugin.yaml` and `__init__.py` before copying.
- **[Risk] Restarting the gateway interrupts any in-flight session.** → Mitigation: this is standard Hermes plugin installation behavior and is expected.
- **[Trade-off] Documentation-driven installation is less deterministic than a dedicated skill.** → Accepted because it eliminates the skill distribution step and matches the observed IOAT behavior.

## Migration Plan

- Not applicable: this is a new documentation-only capability.

## Open Questions

- Where will the zip file be hosted? (GitHub release asset, project downloads directory, or DTR.)
- Should we also provide a manual install fallback in the same section?
