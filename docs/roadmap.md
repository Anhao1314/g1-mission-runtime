# Roadmap and Gated Direction

This file records **direction, not status**. Nothing below is a capability claim until it has passed the repository evidence rule: protocol → source and asset hashes → execution → raw state/events → measured outcome → audit → claim. Items marked `NOT_RUN` have no retained execution evidence. Items marked `BLOCKED` failed or were never authorized; the blocker is part of the record and is not silently retired.

## Currently gated (with the evidence that gates them)

| Item | State | Gating evidence |
| --- | --- | --- |
| Jev decision layer | `BLOCKED` — no online selection, intervention or actuation authority | Phase 3B.1 offline risk role returned `JEV_RISK_ROLE_NOT_SUPPORTED` (7 false-safe decisions among 11 strict violations); Phase 3B.1b early-risk instrumentation was `INCONCLUSIVE`. Retained experiment artifacts are authoritative. |
| Language Runtime / D011 | `BLOCKED` — no natural-language dispatch into this runtime | Language/compiler and Source Authority experiments are offline results; only the reviewed, selectively pinned TEST_ONLY handoff adapter is integrated. |
| Residual recovery vocabulary | `BLOCKED` — `RECOVERY_VOCABULARY_NOT_READY` | Frozen residual recovery characterization found no verified recovery selection. |
| Multi-agent (swarm) execution | `NOT_RUN` | No verified Multi-Swarm runtime exists in the M2 path; earlier future-architecture sketches are not status claims. |
| New policy training (PPO or otherwise) | `NOT_RUN` — out of current path | The verified skill set uses the official pretrained locomotion policy; no new training campaign is authorized. |
| M2.4 cross-state reliability | `PENDING PROPOSAL` | [Design only](../experiments/m2/cross_state_reliability_design_001/design.md); no new physics or reliability result, no acquisition authorization. |

## Proposed next mechanisms (all `NOT_RUN`)

These are the seams the runtime would grow along, each behind the same gates as everything else:

1. **Gated planning interface.** A `Planner` protocol producing Mission IR proposals that must pass the existing deterministic `MissionValidator` before execution; an LLM-backed planner would be TEST_ONLY until independently qualified. Rationale: planning already exists as reviewed structured input (Oracle IR); the mechanism change is the proposal-validation boundary, not free-form dispatch.
2. **Tool-shaped skill registry.** Exposing the closed skill registry with parameter schemas so external decision layers can *propose* calls that the runtime validates and authorizes before dispatch. Rationale: the dispatch boundary already enforces contracts; schemas make the boundary legible to non-robot components.
3. **Mission memory over the evidence ledger.** A derived, read-only view of past mission outcomes and failure taxonomy entries that can be assembled into planning context. Rationale: the ledger is already append-only and source-bound; memory becomes a query over immutable evidence instead of a mutable store.
4. **Learned-policy skill contract.** A skill contract shape for learned policies (observation, instruction, chunked action output) with envelope and evidence fields, so a future learned or multimodal policy enters through the same qualification path as the deterministic skills. Rationale: new capability classes should not bypass the grounding/evaluation layer that gives existing skills their verified scope.
5. **Multi-agent coordination interface.** A stub protocol for coordinating multiple mission executors over shared task graphs. Explicitly `NOT_RUN`; no coordination claim is made or implied.

## Non-goals for the current path

- No online natural-language or LLM dispatch into the runtime.
- No production authorization flow: configuration opt-in remains distinct from authenticated Human Principal Authority.
- No hardware safety claims of any kind; MuJoCo results are simulation results.
- No rewriting or thawing of frozen evidence to support any item above.
