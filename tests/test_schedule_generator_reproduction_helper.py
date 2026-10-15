"""Development reproduction allowance preserves the isolated scientific command."""
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import schedule_generator_release as release


class ReproductionHelperTests(unittest.TestCase):
    def test_combined_reproduction_has_finite_allowance_and_unchanged_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'release'
            result = subprocess.CompletedProcess([], 0, stdout='scientific proof passed\n', stderr='')
            with patch.object(release, 'verify_generator', return_value=[]) as verify, \
                    patch.object(release.subprocess, 'run', return_value=result) as run, \
                    patch('builtins.print') as output:
                self.assertEqual(release.reproduce_generator(target), [])
            verify.assert_called_once_with(target)
            args, kwargs = run.call_args
            self.assertEqual(args, ([sys.executable, '-I', '-S', str(target.resolve() / 'generator.zip'), '--reproduce'],))
            self.assertEqual(kwargs['timeout'], 600)
            self.assertEqual(set(kwargs), {'cwd', 'capture_output', 'text', 'timeout'})
            self.assertTrue(kwargs['capture_output'])
            self.assertTrue(kwargs['text'])
            self.assertEqual(Path(kwargs['cwd']).parent, release.BUILD)
            self.assertFalse(Path(kwargs['cwd']).exists())  # Temporary cwd cleaned after child.
            output.assert_called_once_with('scientific proof passed')

    def test_integrity_failure_never_executes_child(self):
        with patch.object(release, 'verify_generator', return_value=['bad exact member hash']), \
                patch.object(release.subprocess, 'run') as run:
            self.assertEqual(release.reproduce_generator(Path('unused')), ['bad exact member hash'])
            run.assert_not_called()

    def test_nonzero_child_retains_context_and_bounded_stderr(self):
        result = subprocess.CompletedProcess([], 2, stdout='', stderr='failure' * 400)
        with patch.object(release, 'verify_generator', return_value=[]), \
                patch.object(release.subprocess, 'run', return_value=result):
            self.assertEqual(release.reproduce_generator(Path('unused')),
                             ['Frozen runtime reproduction failed: ' + result.stderr[:2000]])

    def test_deadline_failure_still_propagates(self):
        error = subprocess.TimeoutExpired(['actual-isolated-child'], 600)
        with patch.object(release, 'verify_generator', return_value=[]), \
                patch.object(release.subprocess, 'run', side_effect=error):
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                release.reproduce_generator(Path('unused'))
            self.assertIs(caught.exception, error)


if __name__ == '__main__':
    unittest.main()
