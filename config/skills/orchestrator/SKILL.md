---
name: orchestrator
description: 核心工程中枢 - 按需多Agent并行编排引擎（默认关闭）：仅在人工显式确认启用并行后加载，提供 run_workflow 确定性波次调度（写锁隔离、4态Schema、卡死>2次熔断与HITL暂停）及 /teamwork 协作启动Brief生成。
---

# Orchestrator

# Role

Multi-Agent Parallel Orchestrator (On-Demand)

# Mission

Execute human-confirmed parallel waves with deterministic isolation, circuit breaking, and zero unauthorized concurrency.

# Activation & Default-Off Guardrail

- **Default-Off**: Never load or execute parallel orchestration by default. Routine or linear tasks strictly remain on `Single` serial flow.
- **Human-Confirmed Opt-In Only**: Activate ONLY after the user explicitly confirms parallel execution (via `/analyzer`'s `ask_question` opt-in gate or explicit user command).
- **Platform Redline (`/teamwork` / `/swarm`)**: NEVER auto-invoke the `swarm` tool unprompted. When the user chooses `/teamwork`, output the standardized Launch Brief and instruct the user to manually trigger `/teamwork` (or `/swarm`).

# Topology Decision Matrix

| Topology | Activation Condition | Isolation | Control & Circuit Breaker |
| :--- | :--- | :--- | :--- |
| **`Single` (Default)** | Default baseline; single-point or strongly sequential tasks | Shared workspace | Serial `/goal` ($\le 3$ rounds) or `/verifier` (2-Fail) |
| **`invoke_subagent` (Batch $= 2$)** | Concurrency $= 2$, short duration, no multi-wave state machine needed | `Workspace="share"` / `"inherit"` | Master session tracks retries (max 2) and calls `ask_question` directly |
| **`run_workflow` (Deterministic Waves)** | $\ge 2$ independent WBS/modules, frozen L2 contracts, disjoint write domains, batch audits/research | `workspace="share"` (coding) / `"inherit"` (read-only) | Python async state machine: per-item `try/except`, forced JSON `schema`, `max_stalls = 2` + `error_signature` dedup |
| **`/teamwork` (`/swarm`)** | Open-ended cross-module collaboration requiring peer negotiation on shared board | `workspace="share"` | **User-triggered only**; Coordinator/Worker board collaboration |

# Contract-First & Disjoint Write-Lock Protocol

1. **Contract Barrier (L2)**: Before launching any parallel coding wave, verify that cross-module interface/data contracts (`docs/feats/`) are frozen and a lightweight rolling wave ledger (`docs/steps/phase-N-*.md`) declares wave grouping, disjoint Write-Lock Scopes, and deterministic acceptance commands.
2. **Disjoint Write-Lock Scope**: Every concurrent coding worker in the same wave MUST receive a strictly disjoint file/directory write scope and run in `workspace="share"`.
3. **Pre-Merge Write-Lock Audit**: Before merging each `share` workspace back to the main working copy, verify `git diff --name-only` is a strict subset of that worker's declared Write-Lock Scope. Reject and escalate any out-of-scope modification.

# Unified 4-State Worker JSON Schema

All workers dispatched by `run_workflow` MUST terminate via `finish` conforming to this exact JSON schema:

```json
{
  "type": "object",
  "required": ["task_id", "status", "error_signature", "changed_files", "verification_evidence"],
  "properties": {
    "task_id": { "type": "string" },
    "status": {
      "type": "string",
      "enum": ["passed", "retryable_failed", "needs_human_decision", "external_fatal"]
    },
    "error_signature": { "type": "string" },
    "changed_files": { "type": "array", "items": { "type": "string" } },
    "verification_evidence": { "type": "string" },
    "decision_request": {
      "type": "object",
      "properties": {
        "question": { "type": "string" },
        "options": { "type": "array", "items": { "type": "string" }, "maxItems": 3 }
      }
    }
  }
}
```

# Circuit Breaker & HITL Escalation Contract

1. **Silent Self-Healing (`stall_count < 2`)**: When `status == "retryable_failed"` and retry count $< 2$, feed the exact error evidence back to the SAME stateful worker (`await worker(fix_prompt)`) without interrupting the user.
2. **Stall Circuit Breaker (Halt & Dump)**: Immediately trip the breaker (`circuit_broken`) and dump diagnostics to `docs/debug/breaker-<task_id>.md` if EITHER:
   - Consecutive failures reach **3** (i.e., stalled $> 2$ retries), OR
   - Two consecutive attempts produce the **exact same `error_signature`** (local-optimum / oscillation loop).
3. **External Fatal Bypass (1st-Hit Escalation)**: When `status == "external_fatal"` (permission denied, network block, missing host dependency, sandbox block), escalate on the **1st occurrence** with raw evidence; never burn retry budget.
4. **HITL Pause (`needs_human_decision`)**: Since `run_workflow` scripts cannot prompt the user directly, safely exit the wave returning `decision_request` ($\le 3$ options with a recommended default) so the master session invokes `ask_question`.

# `run_workflow` Safe-Parallel Blueprint

Always wrap each `parallel()` item in `try/except` so a single worker exception does NOT cancel healthy sibling workers in the same wave:

```python
# scratch/wave_runner.py
SCHEMA = {
    "type": "object",
    "required": ["task_id", "status", "error_signature", "changed_files", "verification_evidence"],
    "properties": {
        "task_id": {"type": "string"},
        "status": {"type": "string", "enum": ["passed", "retryable_failed", "needs_human_decision", "external_fatal"]},
        "error_signature": {"type": "string"},
        "changed_files": {"type": "array", "items": {"type": "string"}},
        "verification_evidence": {"type": "string"},
        "decision_request": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "options": {"type": "array", "items": {"type": "string"}}
            }
        }
    }
}

async def run_task_with_breaker(task):
    worker = agent(
        f"You execute {task['id']}. Write-Lock Scope: {task['write_lock']}. "
        f"Contract: {task['contract_ref']}. Verify via: {task['verify_cmd']}.",
        schema=SCHEMA,
        role=f"WBS {task['id']}",
        workspace=task.get("workspace", "share"),
    )
    last_sig = None
    try:
        prompt = task["prompt"]
        for attempt in range(3):  # max 2 retries (trip on 3rd failure)
            res = await worker(prompt)
            status = res["status"]
            if status in ("passed", "needs_human_decision", "external_fatal"):
                return res
            sig = res.get("error_signature", "").strip()
            if sig and sig == last_sig:
                res["status"] = "circuit_broken"
                return res
            last_sig = sig
            if attempt < 2:
                prompt = f"Previous attempt failed ({sig}). Evidence: {res['verification_evidence']}. Fix within Write-Lock Scope and re-verify."
        res["status"] = "circuit_broken"
        return res
    except Exception as exc:
        return {
            "task_id": task["id"],
            "status": "external_fatal",
            "error_signature": type(exc).__name__,
            "changed_files": [],
            "verification_evidence": str(exc),
        }
    finally:
        del worker

phase(args["wave_name"])
results = await parallel(args["tasks"], run_task_with_breaker)
log(results)
print(results)
```

# `/teamwork` (`/swarm`) Launch Brief Template

When the user selects `/teamwork`, do NOT call `swarm`. Output the following copy-ready brief and ask the user to invoke `/teamwork`:

```markdown
/teamwork
- **Goal**: <Concise wave/project goal & frozen L2 contract links>
- **Roster & Disjoint Write-Lock Scopes (`workspace="share"`)**:
  - `worker-a`: <Owns WBS/module A; write-lock: path/a/**; verify: cmd>
  - `worker-b`: <Owns WBS/module B; write-lock: path/b/**; verify: cmd>
- **Sync Barriers & Done Criteria**: <Integration gate, git diff write-lock audit, circuit breaker (>2 stalls -> escalate)>
```
