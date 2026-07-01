"""M6 - Your Turn extensions: reasoning budget + carbon-aware scheduling.

Run: python missions/m6_extensions.py
Writes: outputs/extensions.md
"""
from __future__ import annotations

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from missions._common import ROOT, catalog_by_type, load_csv, num
from missions.m2_inference_levers import MODEL_PRICES
from finops import pricing, sustainability


def _optimized_request_cost(row: dict) -> float:
    inp = int(num(row["input_tokens"]))
    out = int(num(row["output_tokens"]))
    cached = int(num(row["cached_input_tokens"]))
    is_batch = bool(int(num(row["is_batch"])))
    pin, pout = MODEL_PRICES[row["route_tier"]]
    return pricing.request_cost(inp, out, pin, pout, cached_in=cached, batch=is_batch)


def reasoning_budget(cap_frac: float = 0.05) -> dict:
    """Measure reasoning traffic cost/energy and estimate savings from a traffic cap."""
    rows = load_csv("token_usage.csv")
    totals = {
        "requests": len(rows),
        "tokens": 0,
        "cost": 0.0,
        "wh": 0.0,
        "reasoning_requests": 0,
        "reasoning_tokens": 0,
        "reasoning_cost": 0.0,
        "reasoning_wh": 0.0,
    }

    for row in rows:
        tokens = int(num(row["input_tokens"])) + int(num(row["output_tokens"]))
        is_reasoning = bool(int(num(row["is_reasoning"])))
        cost = _optimized_request_cost(row)
        wh = sustainability.wh_per_query(tokens, is_reasoning=is_reasoning)

        totals["tokens"] += tokens
        totals["cost"] += cost
        totals["wh"] += wh
        if is_reasoning:
            totals["reasoning_requests"] += 1
            totals["reasoning_tokens"] += tokens
            totals["reasoning_cost"] += cost
            totals["reasoning_wh"] += wh

    current_frac = totals["reasoning_requests"] / totals["requests"] if totals["requests"] else 0.0
    keep_frac = min(1.0, cap_frac / current_frac) if current_frac > 0 else 1.0
    capped_reasoning_wh = totals["reasoning_wh"] * keep_frac
    capped_reasoning_cost = totals["reasoning_cost"] * keep_frac

    return {
        **totals,
        "reasoning_request_pct": current_frac * 100.0,
        "reasoning_token_pct": totals["reasoning_tokens"] / totals["tokens"] * 100.0 if totals["tokens"] else 0.0,
        "reasoning_cost_pct": totals["reasoning_cost"] / totals["cost"] * 100.0 if totals["cost"] else 0.0,
        "reasoning_energy_pct": totals["reasoning_wh"] / totals["wh"] * 100.0 if totals["wh"] else 0.0,
        "cap_frac": cap_frac,
        "cost_saved_by_cap": totals["reasoning_cost"] - capped_reasoning_cost,
        "wh_saved_by_cap": totals["reasoning_wh"] - capped_reasoning_wh,
    }


def carbon_aware_scheduling(source_region: str = "us-east-1", target_region: str = "europe-north1") -> dict:
    """Estimate carbon and electricity savings for moving interruptible jobs."""
    workloads = load_csv("workloads.csv")
    catalog = catalog_by_type()
    jobs = []

    for job in workloads:
        if not bool(int(num(job["interruptible"]))):
            continue
        gpu_type = job["gpu_type"]
        watts = num(catalog[gpu_type]["watts"])
        total_hours = num(job["hours_per_day"]) * num(job["days"]) * int(num(job["num_gpus"]))
        wh = watts * total_hours
        source_carbon = sustainability.carbon_g(wh, source_region)
        target_carbon = sustainability.carbon_g(wh, target_region)
        source_energy_cost = sustainability.energy_cost_usd(wh, source_region)
        target_energy_cost = sustainability.energy_cost_usd(wh, target_region)
        jobs.append({
            "job_id": job["job_id"],
            "gpu_type": gpu_type,
            "wh": wh,
            "source_carbon_g": source_carbon,
            "target_carbon_g": target_carbon,
            "carbon_saved_g": source_carbon - target_carbon,
            "source_energy_cost": source_energy_cost,
            "target_energy_cost": target_energy_cost,
            "energy_cost_saved": source_energy_cost - target_energy_cost,
        })

    total_source_carbon = sum(j["source_carbon_g"] for j in jobs)
    total_target_carbon = sum(j["target_carbon_g"] for j in jobs)
    total_source_energy_cost = sum(j["source_energy_cost"] for j in jobs)
    total_target_energy_cost = sum(j["target_energy_cost"] for j in jobs)

    return {
        "source_region": source_region,
        "target_region": target_region,
        "jobs": jobs,
        "total_source_carbon_g": total_source_carbon,
        "total_target_carbon_g": total_target_carbon,
        "total_carbon_saved_g": total_source_carbon - total_target_carbon,
        "carbon_saved_pct": (1.0 - total_target_carbon / total_source_carbon) * 100.0 if total_source_carbon else 0.0,
        "total_source_energy_cost": total_source_energy_cost,
        "total_target_energy_cost": total_target_energy_cost,
        "energy_cost_saved": total_source_energy_cost - total_target_energy_cost,
    }


def build_extensions_report(reasoning: dict, carbon: dict) -> str:
    lines = [
        "# Lab 25 Your Turn Extensions",
        "",
        "## Extension 1 - Reasoning Budget",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total requests | {reasoning['requests']:,} |",
        f"| Reasoning requests | {reasoning['reasoning_requests']:,} |",
        f"| Reasoning traffic share | {reasoning['reasoning_request_pct']:.1f}% |",
        f"| Reasoning token share | {reasoning['reasoning_token_pct']:.1f}% |",
        f"| Reasoning optimized cost share | {reasoning['reasoning_cost_pct']:.1f}% |",
        f"| Reasoning energy share | {reasoning['reasoning_energy_pct']:.1f}% |",
        f"| Estimated cost saved by capping reasoning to {reasoning['cap_frac']:.0%} traffic | ${reasoning['cost_saved_by_cap']:.2f}/day |",
        f"| Estimated energy saved by cap | {reasoning['wh_saved_by_cap']:.1f} Wh/day |",
        "",
        "Recommendation: only route to reasoning when task complexity is high or when the small/standard model confidence is low. Default traffic should stay on the cheaper non-reasoning route.",
        "",
        "## Extension 2 - Carbon-aware Scheduling",
        "",
        f"Scenario: move interruptible jobs from `{carbon['source_region']}` to `{carbon['target_region']}`.",
        "",
        "| Job | GPU | Energy (kWh) | Carbon saved (kgCO2e) | Energy cost saved |",
        "|---|---|---:|---:|---:|",
    ]
    for job in carbon["jobs"]:
        lines.append(
            f"| {job['job_id']} | {job['gpu_type']} | {job['wh'] / 1000.0:.1f} | "
            f"{job['carbon_saved_g'] / 1000.0:.1f} | ${job['energy_cost_saved']:.2f} |"
        )
    lines += [
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Source carbon | {carbon['total_source_carbon_g'] / 1000.0:.1f} kgCO2e |",
        f"| Target carbon | {carbon['total_target_carbon_g'] / 1000.0:.1f} kgCO2e |",
        f"| Carbon saved | {carbon['total_carbon_saved_g'] / 1000.0:.1f} kgCO2e |",
        f"| Carbon reduction | {carbon['carbon_saved_pct']:.1f}% |",
        f"| Energy cost saved | ${carbon['energy_cost_saved']:.2f} |",
        "",
        "Recommendation: schedule interruptible training/eval jobs in the cleanest practical region when latency and data residency allow it. Keep latency-sensitive inference close to users.",
    ]
    return "\n".join(lines)


def run(verbose: bool = True) -> dict:
    reasoning = reasoning_budget()
    carbon = carbon_aware_scheduling()
    md = build_extensions_report(reasoning, carbon)
    out_path = _os.path.join(ROOT, "outputs", "extensions.md")
    _os.makedirs(_os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    if verbose:
        print("== M6 Your Turn Extensions ==")
        print(md)
        print("\nWritten: outputs/extensions.md")

    return {"reasoning": reasoning, "carbon": carbon, "output": out_path}


if __name__ == "__main__":
    run()
