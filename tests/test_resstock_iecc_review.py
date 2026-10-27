"""The ResStock vs IECC residential evidence report (plan 2026-10-27 R1) reproduces from release 1.4.0."""
import unittest

from scripts import atlas_minor_release, resstock_iecc_review


@unittest.skipUnless((atlas_minor_release.target('1.4.0')/'manifest.json').exists(), 'release 1.4.0 not written')
class ReviewTests(unittest.TestCase):
    def test_report_reproduces_and_pairs_every_recent_dwelling(self):
        from scripts.atlas_exports import Release
        release = Release(release='1.4.0')
        text = resstock_iecc_review.report(release)
        self.assertEqual(resstock_iecc_review.OUTPUT.read_bytes(), text.encode('utf-8'))
        recent = [p for p in release.dwellings.program_ids() if p.startswith('resstock-sdr.')
                  and release.dwellings.stored(p).get('vintage') in resstock_iecc_review.VINTAGES]
        self.assertEqual(len(resstock_iecc_review.pairs(release)), len(recent))
        self.assertEqual(len(recent), 10)


if __name__ == '__main__':
    unittest.main()
