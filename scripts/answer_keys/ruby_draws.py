"""Extract native Ruby 3.2.2 Random draws (10 seeds x 825 draws) for the R1 stream test.

Source: data/schedule-generator/reference-vectors.json (random_vectors), captured
by scripts/reference_schedule_generator.rb on Ruby 3.2.2.

Usage: python -m scripts.answer_keys.ruby_draws
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/schedule-generator/reference-vectors.json"
TARGET = ROOT / "tests/answer_keys/residential/ruby-draws.json"


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    vectors = [{"seed": int(v["seed"]), "draws": [[d["limit"], d["value"]] for d in v["draws"]]}
               for v in data["random_vectors"]]
    payload = {"source": {"file": "data/schedule-generator/reference-vectors.json", "ruby": "3.2.2"}, "vectors": vectors}
    TARGET.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(TARGET.relative_to(ROOT), TARGET.stat().st_size)


if __name__ == "__main__":
    main()
