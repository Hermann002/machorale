"""One-shot script: pre-populate locale/fr/LC_MESSAGES/django.po with msgstr=msgid.

Run AFTER `django-admin makemessages -l fr -l en` and BEFORE editing translations
manually. Idempotent: only fills empty msgstr entries.

Usage:
    pip install polib  # if not already installed
    python scripts/seed_fr_msgstr.py
"""
from __future__ import annotations

from pathlib import Path

import polib


PO_PATH = Path(__file__).resolve().parent.parent / "locale" / "fr" / "LC_MESSAGES" / "django.po"


def main() -> None:
    if not PO_PATH.exists():
        raise SystemExit(f"Not found: {PO_PATH}. Run makemessages first.")

    po = polib.pofile(str(PO_PATH))
    filled = 0
    for entry in po:
        if entry.msgid_plural:
            if not entry.msgstr_plural or not any(entry.msgstr_plural.values()):
                entry.msgstr_plural = {0: entry.msgid, 1: entry.msgid_plural}
                filled += 1
        else:
            if not entry.msgstr:
                entry.msgstr = entry.msgid
                filled += 1
    po.save()
    print(f"Filled {filled} entries in {PO_PATH}")


if __name__ == "__main__":
    main()
