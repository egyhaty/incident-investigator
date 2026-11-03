"""Development counterexamples, not a held-out benchmark."""
from investigator.tools import load_scenario


def cases():
    variants = []
    for source, name, field, value in [
        ("duplicate-ip", "same-mac-repeated", "network", {"arp_responders": ["02:00:00:00:00:22"] * 2}),
        ("memory-crash", "exit-137-without-oom", "workload", {"last_termination": "Error"}),
        ("storage-pressure", "capacity-within-limit", "storage", {"provisioned_gib": 65, "schedulable": True}),
    ]:
        scenario = load_scenario(source)
        scenario["id"] = name
        scenario["title"] = "Synthetic investigation"
        scenario["observations"][field].update(value)
        # Preserve misleading alerts/events deliberately: current measurements
        # no longer establish the original cause. Labels stay outside scenario.
        variants.append((scenario, {"scenario_id": name,
            "expected_diagnosis": "insufficient_evidence",
            "expected_source": "unknown.md", "critical_evidence": "evidence:" + field}))
    # Same generic prompt and resources, but a different decisive observation.
    scenario = load_scenario("insufficient-evidence")
    scenario["id"] = "generic-alert-with-oom"
    scenario["observations"]["workload"].update(
        last_termination="OOMKilled", restarts=8, memory_limit_mib=256, memory_peak_mib=256)
    variants.append((scenario, {"scenario_id": scenario["id"],
        "expected_diagnosis": "container_oom", "expected_source": "memory.md",
        "critical_evidence": "evidence:workload"}))
    return variants
