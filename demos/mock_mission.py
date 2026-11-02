"""Mock mission demo: the runtime's core execution stories without physics.

Four scripted missions run against a deterministic fake session (the same
pattern as ``tests/test_mission_runtime.py``), so the demo needs neither the
MuJoCo assets nor any model weights:

1. REJECTED   - an invalid proposal is refused before any session is created.
2. SUCCESS    - walk 4 m then stop, with an evidence bundle written to disk.
3. FAILURE    - the turn skill fails; its dependent stop node is BLOCKED.
4. STRICT     - a walk that meets its physical envelope but violates the strict
                task envelope triggers STOP_DEPENDENTS under the opt-in strict
                gate, and the decision is written to the event ledger.

Run from the repository root:

    pip install numpy pyyaml lark
    python demos/mock_mission.py

Each run writes its evidence under ``demos/out/<timestamp>/``; nothing is ever
overwritten.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from g1swarm.metrics import RunMetrics  # noqa: E402
from g1swarm.mission import (  # noqa: E402
    CapabilityGrounder,
    MissionExecutor,
    MissionValidator,
    NodeState,
)
from g1swarm.paths import resolve_repo_path  # noqa: E402
from g1swarm.state import RobotState  # noqa: E402

BASE = resolve_repo_path("experiments/baselines/g1_closed_loop_correction_001")

HISTORICAL_SKILL_LIMITS = {
    "turn": {
        "max_abs_angle_deg": 90.0,
        "source_phase": "phase1.1",
        "evidence_ref": "experiments/baselines/g1_skill_characterization_001/summary.json",
    },
    "stand": {
        "max_duration_s": 20.0,
        "default_duration_s": 2.0,
        "source_phase": "phase1.1",
        "evidence_ref": "experiments/baselines/g1_skill_characterization_001/summary.json",
    },
    "stop": {
        "source_phase": "phase1.1",
        "evidence_ref": "experiments/baselines/g1_skill_characterization_001/summary.json",
    },
}


def build_grounder() -> CapabilityGrounder:
    for required in ("risk_map_v1_3.json", "boundary_comparison.json", "capability_map_v1_3.json"):
        if not (BASE / required).is_file():
            sys.exit(
                f"missing grounding evidence: {BASE / required}\n"
                "This demo reads the committed capability/risk maps from\n"
                "experiments/baselines/ - use a full checkout of the repository."
            )
    return CapabilityGrounder(
        risk_map_path=BASE / "risk_map_v1_3.json",
        boundary_comparison_path=BASE / "boundary_comparison.json",
        capability_map_path=BASE / "capability_map_v1_3.json",
        historical_limits=HISTORICAL_SKILL_LIMITS,
    )


# ---------------------------------------------------------------------------
# Scripted session: same shape as the pytest fake, no simulator anywhere.
# ---------------------------------------------------------------------------
def _state_payload(position=(0.0, 0.0, 0.78), yaw_deg: float = 0.0) -> dict:
    half = math.radians(yaw_deg) / 2.0
    return RobotState(
        simulation_time=0.0,
        base_position=position,
        base_orientation=(math.cos(half), 0.0, 0.0, math.sin(half)),
        linear_velocity=(0.0, 0.0, 0.0),
        angular_velocity=(0.0, 0.0, 0.0),
        standing=True,
        fallen=False,
        active_skill=None,
    ).to_dict()


def _node_metrics(*, task: bool = True, physical: bool = True) -> dict:
    return RunMetrics(
        forward_displacement_m=1.0,
        distance_error_m=0.0,
        lateral_drift_m=0.0,
        heading_error_deg=0.0,
        simulation_time_s=1.0,
        physical_success=physical,
        task_success=task,
        failure_type="SUCCESS" if task else "FAILURE",
        failure_reason=None if task else "fake failure",
        controller_memory_resets=1,
        extras={"path_length_m": 1.0, "simulation_steps": 10},
    ).to_dict()


class _State:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def to_dict(self) -> dict:
        return dict(self._payload)


class FakeSession:
    def __init__(self, behaviors: dict[str, str] | None = None) -> None:
        self.behaviors = dict(behaviors or {})
        self.calls: list[tuple[str, str]] = []
        self.closed = False
        self._state = _state_payload()

    def state(self) -> _State:
        return _State(self._state)

    def run_node(self, node, execution_mode: str):
        from g1swarm.mission import NodeExecution

        self.calls.append((node.node_id, execution_mode))
        status = self.behaviors.get(node.node_id, "SUCCESS")
        ok = status == "SUCCESS"
        physically_valid = status not in {"UNSAFE", "NON_FINITE_STATE", "INVALID_CONTROL"}
        return NodeExecution(
            skill=node.skill.value,
            status=status,
            reason=None if ok else f"fake {status}",
            physical_success=physically_valid,
            metrics=_node_metrics(task=ok),
            start_state=dict(self._state),
            end_state=dict(self._state),
            simulation_steps=10,
            memory_resets=1,
            correction={},
        )

    def close(self) -> None:
        self.closed = True


class DriftingSession(FakeSession):
    """Physically healthy walk that violates the 4 m strict drift envelope."""

    def run_node(self, node, execution_mode: str):
        execution = super().run_node(node, execution_mode)
        if node.skill.value == "walk_forward":
            execution.metrics["lateral_drift_m"] = 0.25  # strict limit is 0.20 m
        return execution


PROTOCOL = {
    "protocol_path": "configs/experiments/oracle_mission_runtime_001.yaml",
    "_protocol_sha256": "demo-hash",
    "provenance": {
        "policy_sha256": "cf668f75b90d1abf73d2b87612a6e76bccc61ff7e083b63582d3f6aaa3c1759d",
        "controller_commit": "276801e46c5d433564f24658bac64f254b7d2d4b",
    },
    "skill_parameters": {
        "walk_forward": {
            "tolerance_m": 0.2,
            "speed_mps": 0.5,
            "timeout_min_s": 15.0,
            "timeout_s_per_m": 6.0,
        },
        "turn": {
            "tolerance_deg": 15.0,
            "yaw_rate_radps": 0.5,
            "max_duration_s": 10.0,
            "settle_s": 0.5,
        },
        "stand": {"default_duration_s": 2.0},
        "stop": {"window_s": 1.0, "speed_threshold_mps": 0.10, "max_duration_s": 4.0},
    },
    "grounding": {
        "correction_gains": {
            "heading_only": {"k_heading": 1.5},
            "heading_lateral": {"k_heading": 1.5, "k_lateral": 1.0},
        },
        "correction_limits": {
            "max_yaw_rate_radps": 0.6,
            "deadband_radps": 0.01,
            "oscillation_threshold_radps": 0.05,
        },
    },
}


def _executor(grounder: CapabilityGrounder, out_dir: Path, behaviors=None, session_cls=None, **kwargs):
    created: list = []

    def factory(seed: int):
        session = (session_cls or FakeSession)(behaviors)
        created.append(session)
        return session

    executor = MissionExecutor(
        validator=MissionValidator(),
        grounder=grounder,
        session_factory=factory,
        protocol=PROTOCOL,
        provenance={"git_commit": "demos/mock_mission.py (scripted session)"},
        recorder_root=str(out_dir),
        **kwargs,
    )
    return executor, created


def _mission(steps: list[dict], mission_id: str) -> dict:
    return {"schema_version": "2.0.0", "mission_id": mission_id, "steps": steps}


def _print_result(title: str, result) -> None:
    print(f"\n[{title}]")
    print(f"  state          : {result.state}")
    print(f"  mission_success: {result.mission_success}")
    print(f"  completed/failed: {result.completed_nodes} / {result.failed_node}")
    if result.failure_type:
        print(f"  failure_type   : {result.failure_type}")
    print(f"  physical_success: {result.physical_success}")
    print(f"  sim steps executed: {result.simulation_steps_executed}")


def _print_graph(executor) -> None:
    for node in executor.last_graph.nodes:
        print(f"  node {node.node_id}: {getattr(node.state, 'name', node.state)}")


def _print_events(evidence_dir: Path, mission_id: str) -> None:
    events_path = evidence_dir / mission_id / "events.jsonl"
    if not events_path.is_file():
        return
    events = [json.loads(line)["event"] for line in events_path.read_text(encoding="utf-8").splitlines()]
    print(f"  evidence events ({len(events)}): {' -> '.join(events[:6])} ...")


def main() -> int:
    out_dir = REPO_ROOT / "demos" / "out" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    grounder = build_grounder()
    print(f"evidence output: {out_dir}")

    # ------------------------------------------------------------------
    # 1. REJECTED - invalid proposals never reach a session.
    # ------------------------------------------------------------------
    executor, created = _executor(grounder, out_dir)
    rejected = executor.run(
        _mission([{"id": "s1", "skill": "walk_forward", "parameters": {"distance_m": -2.0}}],
                 mission_id="demo-rejected"),
        write_evidence=True,
    )
    _print_result("act 1: validation gate", rejected)
    print(f"  sessions created: {len(created)} (a rejected proposal dispatches zero physics)")

    # ------------------------------------------------------------------
    # 2. SUCCESS - walk 4 m then stop, evidence bundle on disk.
    # ------------------------------------------------------------------
    executor, created = _executor(grounder, out_dir)
    success = executor.run(
        _mission([
            {"id": "s1", "skill": "walk_forward", "parameters": {"distance_m": 4.0}},
            {"id": "s2", "skill": "stop", "parameters": {}, "depends_on": ["s1"]},
        ], mission_id="demo-success"),
        write_evidence=True,
    )
    _print_result("act 2: nominal mission", success)
    print(f"  dispatch order: {[call[0] for call in created[0].calls]}")
    _print_events(out_dir, "demo-success")

    # ------------------------------------------------------------------
    # 3. FAILURE - the turn skill fails; the dependent stop node is BLOCKED.
    # ------------------------------------------------------------------
    executor, created = _executor(grounder, out_dir, behaviors={"s2": "FAILURE"})
    failure = executor.run(
        _mission([
            {"id": "s1", "skill": "walk_forward", "parameters": {"distance_m": 4.0}},
            {"id": "s2", "skill": "turn", "parameters": {"angle_deg": 45.0}, "depends_on": ["s1"]},
            {"id": "s3", "skill": "stop", "parameters": {}, "depends_on": ["s2"]},
        ], mission_id="demo-failure"),
        write_evidence=True,
    )
    _print_result("act 3: skill failure propagation", failure)
    print("  final task graph:")
    _print_graph(executor)
    print(f"  dispatch order: {[call[0] for call in created[0].calls]} (no retry, s3 never dispatched)")

    # ------------------------------------------------------------------
    # 4. STRICT - physically healthy, task-envelope violation, opt-in gate.
    # ------------------------------------------------------------------
    executor, created = _executor(grounder, out_dir, session_cls=DriftingSession, walk_strict_gate=True)
    strict = executor.run(
        _mission([
            {"id": "s1", "skill": "walk_forward", "parameters": {"distance_m": 4.0}},
            {"id": "s2", "skill": "stop", "parameters": {}, "depends_on": ["s1"]},
        ], mission_id="demo-strict"),
        write_evidence=True,
    )
    _print_result("act 4: strict task-envelope gate", strict)
    decision = strict.nodes[0]["feedback_decision"]
    print(f"  feedback action : {decision['action']}")
    print(f"  violations      : {decision['evaluation']['violations']}")
    print(f"  observed drift  : {decision['observed_metrics']['lateral_drift_m']} m (limit 0.20 m)")
    print("  final task graph:")
    _print_graph(executor)
    _print_events(out_dir, "demo-strict")

    print(
        "\nAll four stories are deterministic replays of scripted sessions.\n"
        "The runtime decisions above - reject, dispatch, block dependents,\n"
        "strict-gate - are the same code paths used with the real MuJoCo session.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
