"""Portability of the immutable base release's notice enumeration."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.common import load_json
from scripts import construction_set_release as legacy


class ConstructionBaseReproductionTests(unittest.TestCase):
    def adapter(self):
        from scripts import construction_base_reproduce
        return construction_base_reproduce

    def test_only_notice_enumeration_is_sorted_without_dropping_files(self):
        module=self.adapter()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);notice=root/'sources/licenses'
            notice.mkdir(parents=True)
            for name in ('z.txt','a.txt','m.txt'):(notice/name).write_text(name)
            original=Path.glob
            def reversed_glob(path,pattern,*args,**kwargs):
                return iter(sorted(original(path,pattern,*args,**kwargs),reverse=True))
            with patch.object(Path,'glob',reversed_glob):
                source=module.ordered_source_path(root)
                self.assertEqual([p.name for p in (source/'sources/licenses').glob('*.txt')],['a.txt','m.txt','z.txt'])
                self.assertEqual([p.name for p in (source/'sources/licenses').glob('*')],['z.txt','m.txt','a.txt'])

    def test_original_check_and_state_restoration(self):
        module=self.adapter();source=legacy.LIBRARY;argv=sys.argv
        def check():
            self.assertEqual(sys.argv[1:],['--check','--quiet'])
            self.assertEqual(legacy.LIBRARY,source)
            self.assertIsNot(type(legacy.LIBRARY),type(source))
        with patch.object(legacy,'main',side_effect=check) as original:
            module.verify_base(quiet=True)
            original.assert_called_once_with()
        self.assertIs(legacy.LIBRARY,source);self.assertIs(sys.argv,argv)

    def test_original_byte_failure_propagates_and_restores_state(self):
        module=self.adapter();source=legacy.LIBRARY;argv=sys.argv
        for problem in ('altered notice','missing notice','extra notice'):
            with self.subTest(problem=problem),patch.object(legacy,'main',side_effect=ValueError(problem)):
                with self.assertRaisesRegex(ValueError,problem):module.verify_base()
                self.assertIs(legacy.LIBRARY,source);self.assertIs(sys.argv,argv)

    def test_frozen_outputs_reproduce_exactly_despite_reversed_notice_order(self):
        module=self.adapter();source=legacy.LIBRARY;original=Path.glob
        release=legacy.load_release();receipt=load_json(legacy.OUTPUT/'completeness.json')
        def reversed_glob(path,pattern,*args,**kwargs):
            values=original(path,pattern,*args,**kwargs)
            return iter(sorted(values,reverse=True)) if path==source/'sources/licenses' else values
        # Full source validation runs in CI. Isolate the serializer/byte checks here.
        with patch.object(legacy,'build_release',return_value=(release,receipt)),patch.object(Path,'glob',reversed_glob):
            with patch.object(sys,'argv',['legacy','--check','--quiet']):
                with self.assertRaisesRegex(ValueError,'manifest.json'):legacy.main()
            module.verify_base(quiet=True)

    def test_changed_missing_or_extra_notice_still_fails_original_byte_checks(self):
        module=self.adapter();source=legacy.LIBRARY;original=Path.glob
        release=legacy.load_release();receipt=load_json(legacy.OUTPUT/'completeness.json')
        notices=sorted((source/'sources/licenses').glob('*.txt'))
        with tempfile.TemporaryDirectory() as directory:
            altered=Path(directory)/notices[0].name
            altered.write_bytes(notices[0].read_bytes()+b'changed')
            extra=Path(directory)/'zz-extra-notice.txt';extra.write_bytes(b'extra')
            for problem in ('altered','missing','extra'):
                def changed_glob(path,pattern,*args,**kwargs):
                    if path!=source/'sources/licenses':return original(path,pattern,*args,**kwargs)
                    if problem=='altered':return iter([altered,*notices[1:]])
                    if problem=='missing':return iter(notices[1:])
                    return iter([*notices,extra])
                with self.subTest(problem=problem),patch.object(legacy,'build_release',return_value=(release,receipt)),patch.object(Path,'glob',changed_glob):
                    with self.assertRaisesRegex(ValueError,'Frozen v2 bytes differ'):
                        module.verify_base(quiet=True)


if __name__=='__main__':unittest.main()
