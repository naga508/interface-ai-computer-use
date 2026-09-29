# Computer-Use Automation System — Technical Report

## 1. Overview

This project implements a focused vertical slice of a computer-use automation system for legacy applications that do not expose convenient APIs.

The central design principle is to separate intelligent workflow discovery from deterministic production execution.

During discovery, an LLM observes and interacts with a real browser session to determine how to accomplish a natural-language goal. The successful interaction trace is then converted into a typed, versioned capability artifact.

Subsequent executions use that capability artifact deterministically and do not require an LLM.

The implemented lifecycle is:

```text
Natural-language goal
        ↓
LLM-driven discovery
        ↓
Observe → Decide → Act
        ↓
Discovery trace
        ↓
CapabilityRecorder
        ↓
Parameterized capability artifact
        ↓
Deterministic ReplayExecutor
        ↓
Structured runtime result
```

The prototype uses a local MockCore banking application to demonstrate a member-balance lookup workflow.

All MockCore member records used in this prototype are synthetic test data. No real banking data, credentials, or customer PII are used in the demonstration.

---

## 2. Demonstrated Vertical Slice

The primary discovery goal used in the live demonstration was:

```text
Open MockCore at http://127.0.0.1:5000,
look up member 12345,
and return their savings balance.
```

A real Gemini-driven discovery run operated against the live browser and selected the following sequence:

```text
navigate
→ type member ID
→ click Search
→ read Savings Balance
→ complete
```

For member `12345`, the discovered result was:

```text
Savings Balance: $8420.37
```

The complete model-driven discovery trace is saved at:

```text
evidence/live_discovery_run.json
```

The discovery trace was then converted into the reusable capability:

```text
artifacts/lookup_member_balance.json
```

The concrete discovery input:

```text
12345
```

was converted into a runtime parameter reference:

```json
{
  "param": "member_id"
}
```

The generated artifact was then replayed without Gemini using a different member:

```text
member_id = 67890
```

and returned:

```text
Savings Balance: $4932.17
```

This demonstrates the core through-line of the project:

```text
model discovers once
        ↓
artifact captures reusable workflow knowledge
        ↓
production replay executes deterministically
```

The workflow is therefore not an exact macro recording of the original member lookup.

---

## 3. Architecture

The implementation is intentionally modular while remaining a lightweight, single-process prototype.

The major discovery path is:

```text
Natural-language goal
        ↓
DiscoveryAgent
        ↓
GeminiDecisionProvider
        ↓
Surface
        ↓
WebSurface
        ↓
Playwright
        ↓
MockCore
```

The recording and replay path is:

```text
DiscoveryResult
        ↓
CapabilityRecorder
        ↓
Capability Artifact
        ↓
ReplayExecutor
        ↓
Surface
        ↓
WebSurface
        ↓
Playwright
```

The most important abstraction boundary is `Surface`.

Higher-level components do not directly depend on Playwright APIs. They use typed actions such as:

```text
navigate
click
type
read
wait_for
```

The current implementation provides `WebSurface`, which translates these logical actions into Playwright operations.

This keeps browser-specific implementation details below the workflow layer and provides a clean seam for other surfaces in the future.

---

## 4. LLM-Driven Discovery

Discovery is implemented as an iterative observe-decide-act loop.

For every iteration:

1. `Surface.perceive()` captures the current application state.
2. The observation includes:
   - current URL,
   - page title,
   - accessibility snapshot,
   - screenshot path.
3. Gemini receives:
   - the user goal,
   - current observation,
   - recent action history.
4. Gemini produces one structured `AgentDecision`.
5. The decision is translated into a typed `Action`.
6. `Surface.act()` executes that action.
7. The new UI state is observed.
8. The process repeats until the goal is complete or the maximum step count is reached.

The successful live run followed approximately:

```text
about:blank
    ↓
Gemini chooses navigate
    ↓
MockCore search page
    ↓
Gemini chooses type
    ↓
member_id = 12345
    ↓
Gemini chooses click Search
    ↓
Member Details
    ↓
Gemini chooses read
    ↓
Savings Balance: $8420.37
    ↓
Gemini marks goal complete
```

The model receives both accessibility information and screenshots.

Accessibility information gives semantic structure such as:

```text
textbox "Member ID"
button "Search"
heading "Member Details"
```

while screenshots preserve additional visual context.

The discovery model is deliberately used only for discovery. Deterministic replay does not call Gemini.

---

## 5. Capability Artifact Design

The capability artifact is the central contract between discovery and production replay.

The generated artifact contains:

- schema version,
- capability ID,
- capability name and description,
- target application metadata,
- typed input parameters,
- typed outputs,
- ordered execution steps,
- target descriptions,
- locator reasoning,
- primary locators,
- fallback locators,
- checkpoints,
- error rules,
- retry policies,
- policy metadata,
- approval state,
- discovery metadata.

An example input declaration is:

```json
{
  "name": "member_id",
  "type": "string",
  "required": true,
  "description": "Member identifier used for account lookup.",
  "sensitive": true
}
```

Instead of storing the discovered value directly in the type step, the capability contains:

```json
{
  "param": "member_id"
}
```

This allows replay callers to provide different values without changing the artifact.

### Target Robustness

Targets are represented semantically rather than as raw mouse coordinates.

For example, the Search button is represented using an accessible role and name:

```json
{
  "strategy": "a11y_role_name",
  "value": {
    "role": "button",
    "name": "Search"
  }
}
```

The Search target also contains a visible-text fallback.

The goal is not to claim that these locators are immune to UI drift. The goal is to make target identification more stable, explainable, and reviewable than absolute coordinates or brittle DOM position assumptions.

### Dynamic Value Normalization

During discovery, the model observed:

```text
Savings Balance: $8420.37
```

Using that complete string as the replay target would make the capability specific to member `12345`.

The recorder therefore normalizes the target to:

```text
Savings Balance
```

while the actual balance is treated as runtime output.

This separates stable target identity from dynamic application data.

### Recorder Scope

The current `CapabilityRecorder` is intentionally specialized to the demonstrated member-balance workflow.

It performs several important transformations:

- converts the discovered member ID into a typed runtime parameter,
- translates discovered targets into artifact locator structures,
- normalizes the dynamic savings-balance target,
- adds output mapping,
- adds the expected success checkpoint,
- adds configured business-outcome and recovery rules,
- records discovery metadata.

It is not intended to be a completely generalized compiler capable of inferring arbitrary capability schemas from any discovery trace.

A successful discovery run also cannot reveal application states that it never encountered.

For example, the successful `12345` discovery did not encounter:

```text
No member found
```

or:

```text
Loading member
```

Those states are therefore supplied as explicit recorder configuration and validated independently during deterministic replay.

`app/artifact/sample.py` remains in the repository as a deterministic test fixture/reference capability for unit tests.

The demonstrated production artifact is generated from the real discovery trace through `CapabilityRecorder`.

---

## 6. Deterministic Replay

The `ReplayExecutor` does not call Gemini or any other LLM.

Replay receives:

```text
Capability artifact
+
runtime parameters
```

For each artifact step, the executor:

1. resolves runtime parameter references,
2. converts artifact locators into Surface targets,
3. attempts the primary locator,
4. uses supported fallbacks when required,
5. performs the declared action,
6. evaluates the step checkpoint,
7. checks declared runtime conditions,
8. performs bounded recovery where appropriate,
9. captures declared outputs.

The same artifact discovered with:

```text
member_id = 12345
```

was successfully replayed with:

```text
member_id = 67890
```

The replay returned:

```text
Savings Balance: $4932.17
```

while explicitly reporting:

```text
LLM usage: NONE
```

This validates the intended separation between model-driven discovery and deterministic production execution.

---

## 7. Runtime Outcome Semantics

The replay layer distinguishes expected application outcomes from automation failures.

### Success

For:

```text
member_id = 67890
```

replay produced:

```json
{
  "status": "SUCCESS",
  "outputs": {
    "savings_balance": "Savings Balance: $4932.17"
  }
}
```

The application and automation both completed successfully.

### Expected Business Outcome

For:

```text
member_id = 99999
```

MockCore displays:

```text
No member found
```

This is not considered broken automation.

The application successfully processed the request and returned an expected business state.

Replay therefore returns:

```json
{
  "status": "BUSINESS_OUTCOME",
  "outputs": {},
  "outcome_code": "MEMBER_NOT_FOUND",
  "step_index": 3
}
```

This distinction is important for downstream systems because an expected business result should not trigger the same operational response as an automation failure.

### Recoverable Runtime Condition

For:

```text
member_id = 55555
```

MockCore initially displays:

```text
Loading member
```

The capability declares this as a recoverable condition with:

```text
recovery = retry
max_attempts = 5
backoff_ms = 500
```

Replay waits and repeatedly checks the expected checkpoint.

When:

```text
Member Details
```

appears, execution continues normally.

The final result is:

```text
Savings Balance: $6100.50
```

### Hard Failure

Conditions that cannot safely continue produce `FAILURE`.

Examples include:

- missing required parameters,
- unsupported replay actions,
- targets that cannot be resolved,
- failed checkpoints with no applicable recovery,
- exhausted retry budgets,
- blocked safety-policy actions.

Where available, the structured result contains diagnostic information such as:

```text
step_index
expected
observed
detail
```

This makes operational failures easier to distinguish and debug.

---

## 8. Human Handoff and Escalation

The system supports escalation to a human while preserving the existing live browser session.

Member:

```text
33333
```

simulates a workflow requiring manual verification.

After Search, MockCore displays:

```text
Manual Verification Required
```

This state does not match the known business-outcome rule or recoverable-loading rule.

Instead of guessing or terminating immediately, the system escalates.

The `SessionController` changes from:

```text
AUTOMATION
```

to:

```text
HUMAN
```

The existing Playwright browser, browser context, page, URL, and application state remain alive.

During the interactive demonstration, the human manually clicks:

```text
Continue
```

in the already-open browser.

The operator then returns to the terminal and presses Enter.

The controller returns to:

```text
AUTOMATION
```

Replay evaluates the original checkpoint again.

When the expected `Member Details` state is present, deterministic execution resumes and reads:

```text
Savings Balance: $7250.40
```

The workflow therefore becomes:

```text
AUTOMATION
     ↓
unexpected UI state
     ↓
HUMAN
     ↓
same live browser session
     ↓
manual action
     ↓
AUTOMATION
     ↓
checkpoint passes
     ↓
continue replay
```

The automated handoff test also exercises the same behavior using a simulated human callback against the existing `Surface`.

---

## 9. Safety

The current safety implementation is deliberately narrow and explicit.

Every browser action passes through the `Surface` boundary before Playwright executes it.

The safety policy currently validates:

- action type,
- navigation host.

Allowed hosts are:

```text
127.0.0.1
localhost
```

Allowed actions include:

```text
navigate
click
type
read
wait_for
```

Navigation to a host outside the allowlist is blocked before browser execution.

The capability also contains:

```json
{
  "policy": {
    "profile": "default",
    "allow_irreversible": false
  }
}
```

The demonstrated capability is intentionally read-oriented.

It does not:

- transfer funds,
- modify an account,
- change credentials,
- create or delete banking records,
- execute other irreversible financial operations.

The current prototype does not perform complete semantic risk classification of every arbitrary click.

A production implementation would add:

- action-specific approval gates,
- richer policy evaluation,
- audit logging,
- state-changing action controls,
- credential isolation,
- PII redaction.

Secrets are supplied through environment variables.

The real Gemini API key exists only in the local:

```text
.env
```

file and is excluded from Git.

The artifact schema also marks `member_id` as sensitive, giving future logging/redaction systems an explicit signal that the value should be handled carefully.

---

## 10. Evidence and Testing

The repository contains evidence from an actual Gemini-driven discovery session:

```text
evidence/live_discovery_run.json
```

The trace records:

- browser observations,
- URL and title,
- accessibility snapshots,
- screenshot references,
- Gemini decisions,
- executed actions,
- action results,
- final result.

The generated capability also records discovery metadata:

```json
{
  "model_used": "gemini-3.5-flash-lite",
  "discovery_run_id": "live-discovery-001"
}
```

Screenshots generated during discovery are stored under:

```text
evidence/screenshots/
```

Bulk development screenshots are intentionally excluded from Git.

At the time of the latest completed test run, the project had:

```text
16 passing tests
```

The test suite covers:

- browser integration,
- Surface abstraction,
- safety policy,
- artifact schema validation,
- artifact serialization,
- artifact storage,
- discovery orchestration,
- parameter substitution,
- deterministic replay,
- success outcomes,
- expected business outcomes,
- recoverable runtime conditions,
- hard failures,
- same-session human escalation.

The handoff test specifically verifies that execution successfully resumes after intervention using the same active browser session.

---

## 11. Surface Heterogeneity

The prototype currently controls a web application, but the higher-level architecture is not intended to make capabilities Playwright-specific.

The core interface is conceptually:

```text
Surface.perceive()
Surface.act()
```

The existing implementation provides:

```text
WebSurface
```

A future system could introduce implementations such as:

```text
DesktopSurface
RemoteBrowserSurface
CitrixSurface
```

while retaining most of the existing:

- discovery logic,
- capability schema,
- replay semantics,
- error classification,
- escalation logic.

The capability describes logical interaction intent and target semantics rather than storing Playwright code directly.

This makes `WebSurface` one concrete execution implementation rather than the definition of the workflow itself.

---

## 12. Multi-Tenant and Application Versioning

The prototype does not implement a complete production multi-tenant capability registry.

However, each capability contains application identity information including:

```text
vendor_app_id
version_range
base_url_pattern
```

A production capability hierarchy could conceptually be organized as:

```text
tenant
  └── vendor application
        └── application version
              └── approved capabilities
```

The capability artifact would contain reusable workflow knowledge.

Tenant-specific information such as:

- credentials,
- runtime input values,
- session state,
- secrets

would remain outside the artifact.

This separation also provides a path for managing UI drift.

A capability can be associated with the application versions for which it has been tested rather than being assumed valid indefinitely.

---

## 13. Deliberate Scope Decisions

The project intentionally prioritizes one complete, inspectable vertical slice instead of broad production infrastructure.

### Implemented

- real Gemini-driven browser discovery,
- observe-decide-act loop,
- accessibility-based perception,
- screenshot perception,
- structured model decisions,
- typed Surface actions,
- Surface abstraction,
- typed capability schema,
- automatic artifact recording,
- runtime parameterization,
- dynamic target normalization,
- deterministic no-LLM replay,
- checkpoints,
- expected business outcomes,
- recoverable retries,
- structured failures,
- host/action safety controls,
- same-session human handoff,
- evidence capture,
- automated tests.

### Deliberately Not Implemented

- distributed execution workers,
- production authentication,
- persistent tenant database,
- capability registry UI,
- fully generalized workflow compiler,
- complete CSS/XPath/visual locator execution,
- desktop-native Surface,
- schema migration framework,
- production telemetry infrastructure,
- generalized PII-redaction pipeline,
- semantic risk classification for arbitrary irreversible actions,
- artifact approval UI.

These are natural production extensions, but they are outside the scope of this prototype.

The implementation instead focuses on making the complete discovery-to-replay lifecycle work and be inspectable.

---

## 14. Key Tradeoffs

### Accessibility-First vs. Pure Vision

The discovery system uses accessibility information as its primary semantic representation while also supplying screenshots.

Accessibility semantics provide useful concepts such as:

```text
role
name
label
visible text
```

and make target selection easier to review.

The tradeoff is that applications with weak or unavailable accessibility metadata would require stronger visual grounding or additional perception methods.

### LLM During Discovery Only

Allowing the LLM to make decisions during every production execution could make the system more adaptive to UI changes.

However, that approach also introduces:

- additional latency,
- API cost,
- nondeterminism,
- additional operational risk.

This prototype therefore uses the model during discovery and converts the successful workflow into deterministic execution.

The tradeoff is that meaningful UI drift can invalidate an artifact and require review or rediscovery.

### Explicit Error Rules

Runtime conditions are declared in the artifact rather than delegated back to Gemini during replay.

This makes production behavior predictable and reviewable.

The tradeoff is that a single successful discovery run cannot expose every possible application state.

Additional business outcomes and recovery conditions may therefore require:

- explicit configuration,
- targeted discovery runs,
- targeted tests.

### Human Escalation Instead of Guessing

When deterministic replay encounters an unknown state, allowing automation or an LLM to guess could be risky.

The prototype instead supports escalation to a human.

This can reduce autonomous completion, but it provides safer behavior while preserving the full application context required for the person to intervene.

---

## 15. Limitations and Next Steps

The current prototype demonstrates the core architecture but is intentionally limited.

The highest-value future extensions would include:

1. generalized capability recording across additional workflows,
2. richer locator strategies,
3. locator stability scoring,
4. application-drift detection,
5. generalized output extraction,
6. artifact approval and lifecycle management,
7. tenant-scoped capability storage,
8. encrypted credential integration,
9. production audit logging and telemetry,
10. stronger PII redaction,
11. semantic policy evaluation for state-changing actions,
12. additional Surface implementations,
13. automated rediscovery when replay detects meaningful UI drift.

These additions would build on the existing architecture rather than requiring a redesign of the core discovery-to-artifact-to-replay model.

---

## 16. Conclusion

The prototype demonstrates the intended separation between intelligent workflow discovery and deterministic production execution.

A real LLM first discovers how to operate the live application:

```text
observe → decide → act
```

The successful discovery trace becomes a typed, versioned capability:

```text
discovery
    ↓
capability artifact
```

That artifact can then execute repeatedly with new runtime parameters:

```text
artifact + runtime inputs
        ↓
deterministic replay
```

without requiring the LLM.

The replay layer also distinguishes:

```text
SUCCESS
BUSINESS_OUTCOME
RECOVERABLE CONDITION
FAILURE
```

and supports escalation to a human when automation encounters an unexpected state it cannot safely resolve.

The human can intervene in the same live browser session, after which deterministic execution can resume.

The resulting system is intentionally small, but it demonstrates the complete through-line from model-driven workflow discovery to reusable computer-use automation.