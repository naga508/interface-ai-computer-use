# Computer-Use Automation System

A prototype computer-use automation system that discovers workflows with an LLM, records them as reusable capability artifacts, and replays them deterministically without an LLM.

The project demonstrates a vertical slice for automating legacy applications that do not expose convenient APIs.

## Core Idea

The system separates workflow discovery from production execution.

```text
Natural-language goal
        ↓
LLM-driven discovery
        ↓
Observe → Decide → Act
        ↓
Recorded capability artifact
        ↓
Parameterized reusable workflow
        ↓
Deterministic replay
        ↓
No LLM required