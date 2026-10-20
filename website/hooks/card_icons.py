"""Inline decorative, self-hosted card icons without changing link semantics."""
from pathlib import Path
import re


ICON_DIR = Path(__file__).resolve().parents[1] / 'overrides' / 'icons'
PLACEHOLDER = re.compile(r'<span class="ea-card-icon" data-icon="([a-z0-9-]+)"></span>')


def on_page_content(html, page, config, files):
    def replace(match):
        svg = (ICON_DIR / (match[1] + '.svg')).read_text(encoding='utf-8').strip()
        return (f'<span class="ea-card-icon" data-card-icon="{match[1]}" aria-hidden="true">{svg}</span>'
                f'<span class="ea-card-backdrop" aria-hidden="true">{svg}</span>')
    return PLACEHOLDER.sub(replace, html)
