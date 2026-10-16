"""Byte-check the frozen v2 base with deterministic source-notice ordering.

The historical generator is itself a frozen input. Its unsorted notice glob
records filesystem enumeration order in manifest.json. Supply the original
lexical order without changing that generator, its hashes, or any byte check.
"""
import argparse
import sys
from pathlib import Path


def ordered_source_path(root):
    notices=Path(root)/'sources/licenses'

    class SourcePath(type(Path())):
        def glob(self,pattern,*args,**kwargs):
            paths=super().glob(pattern,*args,**kwargs)
            if self==notices and pattern=='*.txt':
                return iter(sorted(paths,key=lambda p:p.name))
            return paths

    return SourcePath(root)


def verify_base(*,quiet=False):
    from scripts import construction_set_release as legacy
    source,argv=legacy.LIBRARY,sys.argv
    try:
        legacy.LIBRARY=ordered_source_path(source)
        sys.argv=['construction_set_release','--check']+(['--quiet'] if quiet else [])
        legacy.main()
    finally:
        legacy.LIBRARY=source
        sys.argv=argv


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quiet',action='store_true')
    args=parser.parse_args()
    verify_base(quiet=args.quiet)


if __name__=='__main__':main()
