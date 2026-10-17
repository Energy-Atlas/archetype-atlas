# Residential RNG modes: R1 and R2 equivalence

R1 (`ruby_mt`) replays Ruby 3.2.2 Mersenne Twister streams exactly as OpenStudio-HPXML draws
them; R2 (`pcg64`) uses numpy PCG64 streams spawned from the unit seed. Both run the same
algorithm, so R2 should differ from R1 no more than R1 differs from itself under new seeds.

Criteria were fixed before any R1-versus-R2 comparison, after an R1-only variance pilot:

- standardised effect at most 0.25 SD for mean statistics (daily-mean profile hour by hour, annual totals, annual event counts);
- a unit-permutation test (200 permutations) puts every statistic within 4.0 null standard deviations (also covers daily-total, event duration and start, occupant-type and offset distributions);
- stream primitives (10^6 draws) pass uniformity and cross-stream correlation checks at 99 %.

Fixed absolute margins (1 % of peak per hour, KS 0.03) were dropped as unattainable: occupancy-
driven shapes vary 0.15-0.28 of peak per hour between units, needing 10,000-40,000 units per mode.

| Configuration | Units per mode | Checks | Failures | Worst null z | Worst effect (SD) |
|---|---|---|---|---|---|
| anchorage_ak 1_residents | 500 | 68 | 0 | 2.43 | 0.175 |
| anchorage_ak 2_residents | 500 | 68 | 0 | 2.06 | 0.170 |
| anchorage_ak 4_residents | 500 | 68 | 0 | 1.72 | 0.135 |
| hickory_nc 1_residents | 500 | 68 | 0 | 2.44 | 0.176 |
| hickory_nc 2_residents | 1000 | 68 | 0 | 2.35 | 0.144 |
| hickory_nc 4_residents | 500 | 68 | 0 | 1.68 | 0.140 |
| san_jose_ca 1_residents | 500 | 68 | 0 | 2.39 | 0.174 |
| san_jose_ca 2_residents | 500 | 68 | 0 | 2.16 | 0.199 |
| san_jose_ca 4_residents | 500 | 68 | 0 | 1.76 | 0.147 |

Stream primitives:

- pcg64: KS vs U[0,1) 0.00092, randbelow chi-square 101.6, max cross-stream correlation 0.0138 (pass)
- ruby_mt: KS vs U[0,1) 0.00078, randbelow chi-square 68.6, max cross-stream correlation 0.0151 (pass)

**Verdict: equivalent** (0 failed checks; 4687 s).

Full results: `docs/validation/residential-rng-equivalence.json` (`python -m scripts.studies.rng_equivalence`).
