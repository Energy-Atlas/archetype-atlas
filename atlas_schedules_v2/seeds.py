"""Seed derivation.

Residential units follow OpenStudio-HPXML `BuildResidentialScheduleFile`
(measure.rb:162): each unit's seed is the previous seed times its 1-based
position, so unit order matters (master 42 gives 42, 84, 252, ...).
Commercial operating groups get a SHA-256 seed per group, so rooms that share
a group share one sampled set of operating hours.
"""
import hashlib
import json

from .errors import GeneratorError


def check_master_seed(master: int) -> None:
    if isinstance(master, bool) or not isinstance(master, int) or not 0 <= master < 2**64:
        raise GeneratorError("invalid_seed", "/seed", "Unsigned 64-bit integer required")


def unit_seeds(master: int, count: int) -> list[int]:
    """Cumulative unit seeds for `count` units in order."""
    check_master_seed(master)
    seeds = []
    seed = master
    for position in range(1, count + 1):
        seed *= position
        seeds.append(seed)
    return seeds


def commercial_group_seed(master: int, operating_group: str) -> int:
    """Seed policy `atlas_conditional_seeded_v1`."""
    check_master_seed(master)
    payload = json.dumps(["atlas_conditional_seeded_v1", master, operating_group],
                         ensure_ascii=False, separators=(",", ":")) + "\n"
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest(), "big")
