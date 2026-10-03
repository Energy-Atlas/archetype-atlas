"""Inspect staged (or tracked) blobs for credentials without printing secrets."""
import argparse
import re
import subprocess
from pathlib import PurePosixPath

TOKEN_PATTERNS = [
    re.compile(rb'(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})'),
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(rb'https?://[^\s/@]+:[^\s/@]+@'),
    re.compile(rb'(?i)(?:api[_-]?key|access[_-]?token|password|secret)[ \t]*[=:][ \t]*[\x22\x27]?[A-Za-z0-9_/-]{16,}'),
    re.compile(rb'AKIA[0-9A-Z]{16}'),
]


def scan_blob(path, content):
    name = PurePosixPath(path).name.lower()
    findings = []
    if (name == '.env' or name.startswith('.env.') and name != '.env.example'
            or name in {'.netrc', '.npmrc', 'id_rsa', 'id_ed25519', 'credentials.json'}):
        findings.append(f'{path}: local credential file forbidden')
    for i, pattern in enumerate(TOKEN_PATTERNS, 1):
        if pattern.search(content):
            findings.append(f'{path}: possible credential pattern {i}')
    return findings


def audit_git(staged=True):
    command = ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'] if staged else ['git', 'ls-files', '-z']
    paths = subprocess.check_output(command).decode('utf-8').split('\0')
    findings = []
    for path in filter(None, paths):
        content = subprocess.check_output(['git', 'show', ':'+path])
        findings.extend(scan_blob(path, content))
    return findings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--staged', action='store_true')
    args = p.parse_args()
    findings = audit_git(args.staged)
    if findings:
        print('\n'.join(findings))
        raise SystemExit('Security audit failed; inspect locally without exposing values')
    print('Staged security audit passed' if args.staged else 'Tracked security audit passed')


if __name__ == '__main__':
    main()
