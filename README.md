# g1-mission-runtime

Evidence-native mission runtime for the Unitree G1 in MuJoCo: a reviewed mission plan becomes a validated Task Graph, the Task Graph drives deterministic skill dispatch, every outcome is strictly evaluated, and every decision lands in an append-only evidence ledger.

**In agent terms**, this repository is the *execution layer* of an embodied agent: task planning is a gated interface (proposals must pass a deterministic validator before they reach the runtime), skills are dispatched through a closed registry with strict contracts, failure semantics are explicit (`STOP_DEPENDENTS` blocks the graph, not the robot), and memory over past missions is derivable from immutable evidence rather than a mutable chat log. It does not contain an LLM loop; it is the layer an LLM loop would drive. The system is **not production-ready** and not certified for robot safety.

## Architecture

```text
Reviewed Mission IR ──▶ MissionValidator (static legality, schema sanity)
        │                        │ reject ⇒ REJECTED, zero physics
        ▼                        ▼
   CapabilityGrounder (capability map + risk map + boundary evidence)
        │
        ▼
   TaskGraph ──▶ MissionExecutor ──▶ SkillRouter (closed registry) ──▶ skills
        │                │                                   │
        │                │ strict outcome evaluation          ▼
        │                │ CONTINUE / STOP_DEPENDENTS     MuJoCo state
        │                ▼
        └──▶ event ledger (mission/task-graph/skill/outcome events)
                 │
                 ▼
        Research Console: read-only, integrity-checked, source-bound replay
```

## Quickstart (no physics, no assets, no API keys)

The mock demo runs three missions against a scripted session — a success flow, a skill failure with dependent blocking, and a strict task-envelope violation — writing evidence bundles you can inspect. It needs only the repository checkout (including `experiments/baselines/`) and the light dependencies:

```bash
pip install numpy pyyaml lark
python demos/mock_mission.py
```

Read-only checks of the integration (same scope as CI):

```bash
pip install pytest
python -m pytest tests/test_m2_physical_halt_runtime.py tests/test_mission_runtime.py \
  -q -k "not live_session_runs_a_stop_mission and not live_session_runs_a_grounded_walk"
node --test console/web/data.test.js
```

The Research Console replays committed source-bound G1 states and decisions; it never steps the simulator or reruns an experiment (Windows, from the repository root):

```powershell
py -3.11 console/server.py --data experiments/research_console/m2_post_failure_halt_001 --port 8765
```

Open `http://127.0.0.1:8765/`. The [Console guide](console/README.md) describes evidence inspection and older mechanism replays.

## What runs today

| Capability | Verified scope | Boundary |
| --- | --- | --- |
| G1 skills and walking correction | Official pretrained locomotion policy with deterministic Stand, Walk, Turn and Stop skills; Phase 1.3 heading/lateral correction passed its frozen nominal and two disturbance points. | Simulation and tested envelopes only; no new policy training or general reliability claim. |
| Structured mission execution | Phase 2.0 validated 20/20 frozen Oracle Mission IR missions and rejected 15 negative missions before simulation. | Oracle IR is reviewed structured input, not unrestricted language. |
| M2.0 strict feedback loop | A real strict failure in a 6 m open-loop Walk changed execution from static dispatch of three skills to one failed Walk and two blocked dependents; the normal mission stayed 3/3. | The failed case uses an explicit HIGH-risk, TEST_ONLY override. `STOP_DEPENDENTS` blocks the graph, not robot motion. |
| M2.1 physical handling | An opt-in physical-halt path ran StopSkill after the M2.0 block in one frozen failure state: speed 0.451 → 0.056 m/s in 1.342 s, 0.185 m additional displacement, original strict failure stayed failed. | One previously seen failure state at seed 0; configuration opt-in is not authenticated Human Principal Authority, and this is not a hardware emergency stop. |

The M2.0 [execution report](experiments/m2/closed_loop_mission_001/report.md) and M2.1 [physical-halt report](experiments/m2/post_failure_halt_integration_001/report.md) link to their frozen protocols, raw traces, receipts and audits.

## Latest bounded qualification

M2.3b retains **`PASS_BOUNDED_REAL_MUJOCO_TRUSTED_HANDOFF`**: in one previously seen seed-0 MuJoCo state, a correct TEST_ONLY grant executes a distinct Walk4 → Turn45 → Stop mission (3/3, strict and physical PASS); five invalid controls and accepted-grant replay dispatch zero additional physics. The original task remains FAILED, the complete signed and executed plans match, and no simulator reset occurs after initialization. See the [qualification report](experiments/m2/trusted_handoff_qualification_001/report.md) and [final release gate](experiments/m2/trusted_handoff_qualification_001/release_gate/review.md). PR #7 was merged by merge commit `884edde` and passed independent main acceptance; the [publication decision](ops/decisions/m23b-main-publication.json) records this accepted-main baseline.

The grant is validated only through a trusted, serial, in-process TEST_ONLY entry with a simulated principal. It does not establish production Human Principal Authority, concurrent atomic consume-and-dispatch, durable replay protection, or hardware safety. [M2.4 cross-state design](experiments/m2/cross_state_reliability_design_001/design.md) is a separate pending proposal with no new physics result.

## Current gates

- **Jev decision layer:** offline risk role was `JEV_RISK_ROLE_NOT_SUPPORTED` (7 false-safe decisions among 11 strict violations); no online selection, intervention or actuation authority.
- **Language Runtime / D011:** `BLOCKED`; language/compiler results do not authorize natural-language dispatch into this runtime.
- **Recovery and multi-agent execution:** recovery vocabulary `RECOVERY_VOCABULARY_NOT_READY`; no verified recovery or swarm runtime in the current path.
- **Safety:** task refusal, physical halt request, successful termination and failed termination are distinct states; a successful simulation stop is not physical robot safety.

Direction, rationale and the frozen evidence behind each gate: [docs/roadmap.md](docs/roadmap.md). The broader record lives in [research decisions](docs/research-decisions.md), [negative results](docs/lab-notebook/negative-results.md) and [integrity incidents](docs/lab-notebook/integrity-incidents.md); experiment artifacts remain authoritative for measured claims.

## Evidence rule

**protocol → source and asset hashes → execution → raw state/events → measured outcome → audit → claim.** Keep failed runs and provider/infrastructure failures distinct. Do not overwrite frozen evidence to improve a verdict.

## Repository map

| Path | Role |
| --- | --- |
| `src/g1swarm/mission/` | Mission IR, grounding, Task Graph, deterministic feedback executor, trusted handoff, live session |
| `src/g1swarm/skills/`, `control/`, `simulation/` | G1 skills, official-policy controller port, MuJoCo adapter |
| `experiments/` | Frozen protocols, raw evidence, receipts, audits, reports and Console replay artifacts |
| `console/` | Read-only integrity-checked evidence server and synchronized robot/trajectory UI |
| `demos/mock_mission.py` | Scripted-session demo of the three core execution stories (no physics required) |
| `scripts/research_ops.py`, `ops/` | Research context, workflow telemetry and reviewed selection |
| `docs/lab-notebook/` | Historical research narrative, negative results and integrity record |

## Development environment

The original G1 physics studies use native Windows, Python 3.11, pinned Unitree assets and the repository-local virtual environment. Check the frozen protocol and asset hashes before any new experiment.

```powershell
py -3.11 -m venv .venv
.\scripts\enter.ps1
pip install -e ".[dev]"
pip install torch --index-url https://download.pytorch.org/whl/cu130
.\scripts\fetch_g1_models.ps1
```

The official pretrained `motion.pt` and G1 model assets are fetched into ignored `third_party/`; they are not committed. Use the [Phase 1 compatibility notes](experiments/baselines/g1_compat_spike/README.md) and the frozen experiment protocols before attempting a physics reproduction. The [Research Ops guide](.agents/skills/g1-research-ops/SKILL.md) describes the claim and closeout workflow used to develop this repository.

Apache-2.0; see [LICENSE](LICENSE).
