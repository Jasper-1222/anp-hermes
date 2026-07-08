## [HEAL-20260708-001] openspec_warning_cleanup

**Logged**: 2026-07-08T15:27:19+08:00
**Status**: verified
**Trigger**: tool-failure
**Active-Context**: OpenSpec sync/archive warning cleanup
**Area**: openspec
**Priority**: medium

### Failure
Two warnings remained after archiving `expose-hermes-tools`:

1. `openspec/changes/archive/2026-07-08-expose-hermes-tools/tasks.md` still had one incomplete checkbox:
   `- [ ] 6.7 通过 /opsx:verify expose-hermes-tools 后，同步 main specs 并归档。`
2. `openspec validate --all` failed because `openspec/specs/anp-auth-error-classification/spec.md` had a requirement text using `MAY` instead of the validator-required `SHALL` or `MUST` keyword:
   `requirements.5.text: Requirement must contain SHALL or MUST keyword`

### Diagnosis
The incomplete checkbox was a state-ordering issue: `expose-hermes-tools` had already been synced and archived, so invoking `/opsx:verify expose-hermes-tools` after archive failed because the active change no longer existed. The fix was to temporarily restore the archived change to active, run the OpenSpec artifact/task verification command, then mark task 6.7 complete and archive again.

The validation failure was a spec-format issue, not an implementation issue. OpenSpec validates each requirement body and requires `SHALL` or `MUST`; `anp-auth-error-classification` used `MAY` for `Challenge 头转发`. A matching main spec (`anp-platform-adapter`) already states this same behavior with `SHALL`, so the minimal consistent fix was to change that requirement sentence from `MAY` to `SHALL`.

### Fix
- Temporarily moved `openspec/changes/archive/2026-07-08-expose-hermes-tools` back to `openspec/changes/expose-hermes-tools` for verification.
- Changed `openspec/specs/anp-auth-error-classification/spec.md` requirement text from `MAY` to `SHALL` for challenge header forwarding.
- Marked task 6.7 complete in `openspec/changes/expose-hermes-tools/tasks.md` after verification.
- Moved the change back to `openspec/changes/archive/2026-07-08-expose-hermes-tools`.

### Verification
Ran:

```bash
openspec validate anp-auth-error-classification --type spec && \
openspec instructions apply --change "expose-hermes-tools" --json && \
openspec validate expose-hermes-tools --type change && \
openspec validate --all
```

Observed:

- `Specification 'anp-auth-error-classification' is valid`
- `progress.total: 31`, `progress.complete: 31`, `progress.remaining: 0`, `state: "all_done"`
- `Change 'expose-hermes-tools' is valid`
- `Totals: 15 passed, 0 failed (15 items)` while the change was active

Then re-archived and ran:

```bash
openspec list --json && openspec validate --all
```

Observed:

- Active changes list: `"changes": []`
- `Totals: 14 passed, 0 failed (14 items)`
- Archive path exists: `openspec/changes/archive/2026-07-08-expose-hermes-tools`

### Metadata
- Related Files: openspec/specs/anp-auth-error-classification/spec.md, openspec/changes/archive/2026-07-08-expose-hermes-tools/tasks.md
- See Also: none
- Pattern-Key: openspec.spec_validation
- Recurrence-Count: 1
- First-Seen / Last-Seen: 2026-07-08

---

## [HEAL-20260708-002] github_https_push_timeout

**Logged**: 2026-07-08T16:44:23+08:00
**Status**: verified
**Trigger**: external-change
**Active-Context**: ship push to master
**Area**: git/github
**Priority**: medium

### Failure
`git push origin master` failed while pushing the merged `master` branch:

```text
fatal: unable to access 'https://github.com/Jasper-1222/anp-hermes.git/': Failed to connect to github.com port 443 after 136905 ms: Couldn't connect to server
```

### Diagnosis
The repository state and verification gate were clean before pushing, so the failure was not caused by local git state. A direct WSL2 socket probe to `github.com:443` later succeeded, showing the issue was transient HTTPS connectivity to GitHub rather than a repository or credential problem.

### Fix
No project file patch was needed. Retried the push after confirming `github.com:443` connectivity:

```bash
python3 - <<'PY2'
import socket
s=socket.socket(); s.settimeout(20); s.connect(('github.com', 443)); s.close()
PY2
git push origin master
```

### Verification
The connectivity probe returned `connect ok`, and the retry returned:

```text
Everything up-to-date
```

This verified that the previous push had reached the remote or the remote had become synchronized by the time connectivity recovered.

### Metadata
- Related Files: none
- See Also: none
- Pattern-Key: external.github_https_timeout
- Recurrence-Count: 1
- First-Seen / Last-Seen: 2026-07-08

---
