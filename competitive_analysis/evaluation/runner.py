"""
Evaluation runner - executes scenarios and generates benchmark reports.

Usage:
    python -m competitive_analysis.evaluation.runner --scenario saas_pm_tools
"""

from __future__ import annotations

import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .metrics import evaluate_run
from .scenarios import SCENARIOS

logger = logging.getLogger("competitive_analysis.evaluation")


def run_scenario(
    scenario_id: str,
    workflow,
    output_dir: str = "./outputs/eval",
) -> Dict[str, Any]:
    """
    Run one evaluation scenario and return metrics.

    Args:
        scenario_id: ID from SCENARIOS list
        workflow: CompetitiveAnalysisWorkflow instance
        output_dir: Where to save evaluation results
    """
    scenario = next((s for s in SCENARIOS if s["id"] == scenario_id), None)
    if not scenario:
        raise ValueError(f"Unknown scenario: {scenario_id}")

    logger.info("Running scenario: %s", scenario["name"])
    started = time.perf_counter()

    # Run the workflow
    final_state = workflow.run(
        query=scenario["query"],
        competitors=scenario["competitors"],
    )

    elapsed_ms = int(round((time.perf_counter() - started) * 1000))

    # Evaluate
    trace = final_state.get("trace")
    metrics = evaluate_run(final_state, trace)
    metrics["scenario_id"] = scenario_id
    metrics["elapsed_ms"] = elapsed_ms

    # Check thresholds
    thresholds = scenario.get("thresholds", {})
    failed = []
    for metric_name, threshold in thresholds.items():
        actual = metrics.get(metric_name, 0)
        if isinstance(actual, dict):
            continue
        if float(actual) < float(threshold):
            failed.append({"metric": metric_name, "actual": actual, "threshold": threshold})

    metrics["threshold_check"] = {
        "passed": len(failed) == 0,
        "failed": failed,
    }

    # Save results
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    result_file = out_path / f"{scenario_id}_eval.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)

    logger.info("Scenario %s: overall_score=%.4f, passed=%s",
                scenario_id, metrics["overall_score"], metrics["threshold_check"]["passed"])

    return metrics


def run_all_scenarios(workflow, output_dir: str = "./outputs/eval") -> list[Dict[str, Any]]:
    """Run all predefined scenarios and return results."""
    results = []
    for scenario in SCENARIOS:
        try:
            result = run_scenario(scenario["id"], workflow, output_dir)
            results.append(result)
        except Exception as e:
            logger.error("Scenario %s failed: %s", scenario["id"], e)
            results.append({"scenario_id": scenario["id"], "error": str(e)})
    return results
