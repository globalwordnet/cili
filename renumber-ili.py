#!/usr/bin/env python3

"""
Script to renumber proposed ILI concepts in ili.ttl so IDs stay consecutive.

When reviewing a proposal PR, unwanted concepts (duplicates, rejected
candidates, ...) are simply deleted from ili.ttl by hand. That leaves gaps
in the ID sequence. This script closes them: every concept in ili.ttl whose
ID does not exist in the base revision (by default origin/master) is
treated as proposed, and is renumbered consecutively, in file order,
starting from the base revision's highest ID + 1. References to renumbered
concepts (e.g. ili:supersededBy <iNNN>) are updated to match.

Concepts that exist in the base revision are never renumbered; the script
fails if any of them has been deleted, or if a reference points at a
proposed concept that was deleted.

See PROPOSING_ILIS.md for the proposal workflow this script is part of.
This script does not touch git history; commit the result yourself.

Requirements:
    - Python 3.6+
    - git (to read the base revision)
Usage:
    python3 renumber-ili.py [--base REF] [--dry-run] [ili.ttl]
Example:
    python3 renumber-ili.py --base origin/master ili.ttl

"""

import argparse
import re
import subprocess
import sys

# A concept block starts with "<iNNN>" at the start of a line.
CONCEPT = re.compile(r"^<i(\d+)>", re.M)
# Any reference to a concept, whether subject or object.
REF = re.compile(r"<i(\d+)>")


def concept_ids(text):
    return [int(m.group(1)) for m in CONCEPT.finditer(text)]


def read_base(ref, path):
    try:
        return subprocess.check_output(
            ["git", "show", "%s:%s" % (ref, path)],
            stderr=subprocess.PIPE, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        sys.exit("Could not read %s:%s from git: %s" % (ref, path, e.stderr.strip()))


def check_sequence(ids):
    """Returns 0 if ids are exactly 1, 2, 3, ... in file order, else 1."""
    for pos, i in enumerate(ids, start=1):
        if i != pos:
            print("ID sequence broken at concept #%d: expected i%d, found i%d. "
                  "Run renumber-ili.py to close gaps." % (pos, pos, i),
                  file=sys.stderr)
            return 1
    print("OK: %d concepts, i1-i%d, ascending with no gaps" % (len(ids), len(ids)),
          file=sys.stderr)
    return 0


def renumber(text, base_ids):
    """Returns (new_text, mapping of old -> new IDs for changed concepts)."""
    ids = concept_ids(text)
    missing = base_ids - set(ids)
    if missing:
        sys.exit("Existing concepts were deleted (not allowed): %s" %
                 ", ".join("i%d" % i for i in sorted(missing)[:10]))
    if len(set(ids)) != len(ids):
        sys.exit("Duplicate concept IDs in file; resolve these first.")

    next_id = max(base_ids) + 1
    mapping = {}
    for i in ids:
        if i not in base_ids:
            mapping[i] = next_id
            next_id += 1
    changed = {old: new for old, new in mapping.items() if old != new}

    # Every reference must resolve to a concept that is still in the file.
    known = set(ids)
    for m in REF.finditer(text):
        if int(m.group(1)) not in known:
            sys.exit("Reference to <i%s>, which is not in the file "
                     "(was a referenced concept deleted?)" % m.group(1))

    # Single simultaneous pass, so renumbering never collides with itself.
    new_text = REF.sub(
        lambda m: "<i%d>" % mapping.get(int(m.group(1)), int(m.group(1))), text)
    return new_text, changed


def main():
    parser = argparse.ArgumentParser(
        description="Renumber proposed ILI concepts so IDs are consecutive")
    parser.add_argument("ili", nargs="?", default="ili.ttl",
                        help="the ili.ttl to renumber in place (default: ili.ttl)")
    parser.add_argument("--base", default="origin/master",
                        help="git revision holding the accepted ili.ttl "
                             "(default: origin/master)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change without writing")
    parser.add_argument("--check", action="store_true",
                        help="only verify that concept IDs in the file are "
                             "ascending and consecutive from i1 (exit 1 "
                             "otherwise); used by CI, ignores --base")
    args = parser.parse_args()

    with open(args.ili, encoding="utf-8") as f:
        text = f.read()
    if args.check:
        sys.exit(check_sequence(concept_ids(text)))
    base_ids = set(concept_ids(read_base(args.base, args.ili)))
    new_text, changed = renumber(text, base_ids)

    ids = concept_ids(new_text)
    proposed = [i for i in ids if i not in base_ids]
    print("%d proposed concepts (i%d-i%d); %d renumbered" % (
        len(proposed), min(proposed, default=0), max(proposed, default=0),
        len(changed)), file=sys.stderr)
    if not args.dry_run and changed:
        with open(args.ili, "w", encoding="utf-8") as f:
            f.write(new_text)


if __name__ == "__main__":
    main()
