"""Capture compact legacy output for the two A5 case-matrix requests (orchestration answer key).

The case matrix (data/generator-releases/v0.8.0/manifest.json, case_matrix)
holds two v1.2 requests that together exercise apartment unit chains (N = 0 and
N > 0), caller-unit water, Retail/Restaurant source parents, shared physical
services and commercial operating groups (463 owners). The frozen v0.8.0
legacy generator (build/task-10/v080-package) is run on each, seed from the
request. Per owner: identity, every schedule as distinct days plus a day index
(stochastic residential schedules as daily sums and sampled hours), and every
binding's amplitude and annual total.

Usage: python -m scripts.answer_keys.legacy_case_matrix
"""
import gzip
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "build/task-10/v080-package"
MANIFEST = ROOT / "data/generator-releases/v0.8.0/manifest.json"
TARGET = ROOT / "tests/answer_keys/orchestration/case-matrix.json.gz"
SAMPLE_HOURS = list(range(0, 8760, 37))


def _pack(values: list) -> dict:
    days, lookup, index = [], {}, []
    for day in range(365):
        key = tuple(values[24 * day:24 * (day + 1)])
        if key not in lookup:
            lookup[key] = len(days)
            days.append(list(key))
        index.append(lookup[key])
    if len(days) > 60:  # stochastic: keep a signature
        array = np.asarray(values)
        return {"daily": array.reshape(365, 24).sum(axis=1).tolist(), "sample": array[SAMPLE_HOURS].tolist()}
    return {"days": days, "index": index}


def main() -> None:
    sys.path.insert(0, str(PACKAGE))
    from atlas_schedules import generate  # the legacy package
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cases = []
    for case in manifest["case_matrix"]["cases"]:
        request = json.loads((PACKAGE / case["request"]["path"]).read_text(encoding="utf-8"))
        started = time.time()
        params = request["params"]
        seed = request["seed"]
        bundle = generate(params, seed)
        owners = []
        for constituent in bundle["constituents"]:
            owners.append({
                "instance_key": constituent["instance_key"],
                "program_id": constituent.get("program_id"),
                "owner_kind": constituent.get("owner_kind"),
                "schedules": {slot: _pack(bundle["schedules"][sid]["values"])
                              for slot, sid in constituent["schedule_ids"].items()},
                "bindings": [{"slot": bundle["bindings"][i].get("slot"),
                              "amplitude": bundle["bindings"][i].get("effective_magnitude", {}).get("value"),
                              "annual_total": bundle["bindings"][i].get("reference_target", {}).get("total")}
                             for i in constituent["binding_indices"]],
            })
        cases.append({"case_id": case["case_id"], "seed": seed, "request": params, "owners": owners,
                      "generation": {k: bundle["generation"].get(k) for k in ("unit_seeds", "residential_unit_order")}})
        print(case["case_id"], len(owners), "owners", f"{time.time() - started:.0f}s", flush=True)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": {"package": "data/generator-releases/v0.8.0/generator.zip", "manifest": "case_matrix"},
               "cases": cases}
    TARGET.write_bytes(gzip.compress(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"), mtime=0))
    print(TARGET.relative_to(ROOT), TARGET.stat().st_size)


if __name__ == "__main__":
    main()
