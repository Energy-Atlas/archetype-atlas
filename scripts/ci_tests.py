"""Run one shard of the unit suite, so CI can run the shards as parallel jobs.

python -m scripts.ci_tests --shard atlas        # every test outside tests/schedules
python -m scripts.ci_tests --shard schedules    # tests/schedules

The shards partition `python -m unittest discover -s tests`: every discovered test,
including a module that fails to import, belongs to exactly one shard.
"""
import argparse
import sys
import unittest

from scripts.common import ROOT

SHARDS = ('atlas', 'schedules')


def shard_of(test):
    return 'schedules' if type(test).__module__.startswith('schedules.') else 'atlas'


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def shards():
    """{shard: [test, ...]} over the whole discovered suite."""
    out = {name: [] for name in SHARDS}
    for test in flatten(unittest.defaultTestLoader.discover(str(ROOT/'tests'))):
        out[shard_of(test)].append(test)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--shard', choices=SHARDS, required=True)
    args = parser.parse_args(argv)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(shards()[args.shard]))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
