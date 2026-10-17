"""Write docs/validation/residential-rng-equivalence.md from the study's JSON result.

Usage: python -m scripts.studies.rng_report
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/validation/residential-rng-equivalence.json"
TARGET = ROOT / "docs/validation/residential-rng-equivalence.md"


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    criteria = data["criteria"]
    lines = [
        "# Residential RNG modes: R1 and R2 equivalence",
        "",
        "R1 (`ruby_mt`) replays Ruby 3.2.2 Mersenne Twister streams exactly as OpenStudio-HPXML draws",
        "them; R2 (`pcg64`) uses numpy PCG64 streams spawned from the unit seed. Both run the same",
        "algorithm, so R2 should differ from R1 no more than R1 differs from itself under new seeds.",
        "",
        "Criteria were fixed before any R1-versus-R2 comparison, after an R1-only variance pilot:",
        "",
        f"- standardised effect at most {criteria['effect_margin_sd']} SD for mean statistics "
        "(daily-mean profile hour by hour, annual totals, annual event counts);",
        f"- a unit-permutation test ({criteria['permutations']} permutations) puts every statistic within "
        f"{criteria['null_z_limit']} null standard deviations (also covers daily-total, event duration and "
        "start, occupant-type and offset distributions);",
        "- stream primitives (10^6 draws) pass uniformity and cross-stream correlation checks at 99 %.",
        "",
        "Fixed absolute margins (1 % of peak per hour, KS 0.03) were dropped as unattainable: occupancy-",
        "driven shapes vary 0.15-0.28 of peak per hour between units, needing 10,000-40,000 units per mode.",
        "",
        "| Configuration | Units per mode | Checks | Failures | Worst null z | Worst effect (SD) |",
        "|---|---|---|---|---|---|",
    ]
    for key, config in data["configurations"].items():
        report = config["report"]
        worst_z = max(v["null_z"] for v in report.values())
        effects = [v["effect_sd"] for v in report.values() if "effect_sd" in v]
        lines.append(f"| {key.replace('__', ' ')} | {config['seeds']} | {len(report)} | {len(config['failures'])} "
                     f"| {worst_z:.2f} | {max(effects):.3f} |")
    lines += ["", "Stream primitives:", ""]
    for mode, result in data["primitives"].items():
        lines.append(f"- {mode}: KS vs U[0,1) {result['random_ks_vs_uniform']:.5f}, "
                     f"randbelow chi-square {result['randbelow97_chi_square']:.1f}, "
                     f"max cross-stream correlation {result['max_cross_stream_correlation']:.4f} "
                     f"({'pass' if result['equivalent'] else 'FAIL'})")
    verdict = data["overall"]
    lines += ["", f"**Verdict: {'equivalent' if verdict['equivalent'] else 'not shown equivalent'}** "
              f"({len(verdict['failures'])} failed checks; {verdict['seconds']} s).", "",
              "Full results: `docs/validation/residential-rng-equivalence.json` "
              "(`python -m scripts.studies.rng_equivalence`)."]
    TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(TARGET.relative_to(ROOT))


if __name__ == "__main__":
    main()
