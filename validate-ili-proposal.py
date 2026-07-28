#!/usr/bin/env python3

"""
Script that generates the CI comment for an ILI-proposal pull request
(issue #9, Phase 2). Invoked by
.github/workflows/validate-ili-proposal.yml; not meant to be run by
contributors themselves (see propose-ili.py for that).

Unlike propose-ili.py, this script never sees the contributor's original
WN-LMF file - a pull_request CI job only has the git history, so it only
has two versions of ili.ttl: the PR's target branch, and the PR's own
branch. It:

  1. Uses `git diff` to find which <iNNNNN> subjects this PR's commits
     actually added (not a graph-level set difference - see the note on
     collisions below for why that matters).
  2. Checks each added subject's shape (correct rdf:type, an @en
     skos:definition, dc:source, ili:status ili:provisional).
  3. Flags an added id that already exists on the target branch as a
     collision: two proposal PRs opened around the same time can both
     compute the same next-available id, and because both diffs are
     pure appends, git won't necessarily flag this as a merge conflict
     on its own (see PROPOSING_ILIS.md).
  4. Re-runs the semantic duplicate check (MiniLM cosine similarity)
     against every definition already on the target branch.

Renders one Markdown comment, meant to be posted (or, on a later push,
updated in place) on the pull request.

Requirements:
    - Python 3.6+
    - rdflib
    - sentence-transformers
Usage:
    python3 validate-ili-proposal.py --base-ili BASE_ILI.ttl \
        --diff DIFF_FILE --head-ili ili.ttl [--output comment.md]

"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rdflib import Graph, Namespace
from rdflib.namespace import RDF, SKOS, DC

ILI = Namespace('http://globalwordnet.org/cili/')
STATUS = Namespace('https://globalwordnet.github.io/cili/ontology.xml#')
MARKER = '<!-- ili-validation-report -->'
MINILM_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
DEFAULT_SIMILARITY_THRESHOLD = 0.95

# matches the start of a concept block, e.g. `<i117660>\ta\t<Concept> ;`
# (the exact format propose-ili.py emits) on a line the diff *added*.
ADDED_SUBJECT_RE = re.compile(r'^\+<(i\d+)>\s+a\s+')
# a removed line, excluding the `--- a/...` unified-diff file header
# (content lines are tab-indented, so `-\S` alone would miss most of them)
REMOVED_CONTENT_RE = re.compile(r'^-(?!--)')


def load_entries(ttl_path: Path) -> Dict[str, Dict]:
    g = Graph()
    g.parse(ttl_path, format='ttl')
    entries = {}
    for subj in g.subjects(RDF.type, None):
        rdf_type = g.value(subj, RDF.type)
        if rdf_type not in (ILI.Concept, ILI.Instance):
            continue
        sid = subj.rpartition('/')[2]
        entries[sid] = {
            'type': rdf_type,
            'definition': g.value(subj, SKOS.definition),
            'source': g.value(subj, DC.source),
            'status': g.value(subj, STATUS.status),
        }
    return entries


def added_ids_from_diff(diff_text: str) -> Tuple[List[str], bool]:
    """Returns (ids added by this PR's diff, whether anything else was removed)."""
    added = []
    removed_other_content = False
    for line in diff_text.splitlines():
        m = ADDED_SUBJECT_RE.match(line)
        if m:
            added.append(m.group(1))
        elif REMOVED_CONTENT_RE.match(line) and not line.startswith('---'):
            removed_other_content = True
    return added, removed_other_content


def shape_errors_for(entry: Dict) -> List[str]:
    errors = []
    if entry['type'] not in (ILI.Concept, ILI.Instance):
        errors.append('missing or invalid `a <Concept>`/`<Instance>`')
    definition = entry['definition']
    if definition is None or getattr(definition, 'language', None) != 'en':
        errors.append('missing or non-`@en` `skos:definition`')
    if entry['source'] is None:
        errors.append('missing `dc:source`')
    if entry['status'] != STATUS.provisional:
        errors.append('missing `ili:status ili:provisional`')
    return errors


def find_duplicates(
    added_ids: List[str],
    head_entries: Dict[str, Dict],
    base_entries: Dict[str, Dict],
    threshold: float,
) -> Dict[str, Tuple[str, str, float]]:
    checkable = [sid for sid in added_ids if head_entries[sid]['definition'] is not None]
    base_with_defs = [(sid, e['definition']) for sid, e in base_entries.items() if e['definition'] is not None]
    if not checkable or not base_with_defs:
        return {}

    from sentence_transformers import SentenceTransformer, util

    model = SentenceTransformer(MINILM_MODEL)
    base_ids = [sid for sid, _ in base_with_defs]
    base_texts = [str(defn) for _, defn in base_with_defs]
    base_embeddings = model.encode(
        base_texts, normalize_embeddings=True, convert_to_tensor=True, show_progress_bar=False)
    candidate_texts = [str(head_entries[sid]['definition']) for sid in checkable]
    candidate_embeddings = model.encode(
        candidate_texts, normalize_embeddings=True, convert_to_tensor=True, show_progress_bar=False)

    scores = util.cos_sim(candidate_embeddings, base_embeddings)
    results = {}
    for sid, row in zip(checkable, scores):
        best_score, best_index = float(row.max()), int(row.argmax())
        if best_score >= threshold:
            results[sid] = (base_ids[best_index], base_texts[best_index], best_score)
    return results


def render_comment(
    added_ids: List[str],
    head_entries: Dict[str, Dict],
    base_entries: Dict[str, Dict],
    shape_problems: Dict[str, List[str]],
    collisions: List[str],
    removed_other_content: bool,
    duplicates: Dict[str, Tuple[str, str, float]],
) -> str:
    lines = [MARKER, '## ILI proposal validation', '']

    if not added_ids:
        lines.append(
            'No new `<iNNNNN>` concepts were added by this diff (relative to the target branch), '
            'so there is nothing for this check to validate.')
        return '\n'.join(lines)

    status_bits = []
    status_bits.append('❌ shape errors' if shape_problems else '✅ shape checks passed')
    status_bits.append('❌ ID collisions with target branch' if collisions else '✅ no ID collisions with target branch')
    status_bits.append(f'⚠️ {len(duplicates)} flagged for possible duplication' if duplicates
                        else '✅ no likely duplicates found')
    lines.append(f'{len(added_ids)} candidate(s) in this diff. ' + ' · '.join(status_bits))
    lines.append('')

    if removed_other_content:
        lines.append(
            '> ⚠️ This diff also removes or modifies existing lines in `ili.ttl`, not just appends '
            'new concepts. Please double-check nothing outside the new proposals was touched.')
        lines.append('')

    if collisions:
        lines.append(f'### {len(collisions)} ID collision(s)')
        lines.append(
            'These ids were added by this PR but already exist on the target branch - likely '
            'because another proposal PR merged first. Rerun `propose-ili.py` against the latest '
            'target branch and push again; it always allocates from the current file.')
        lines.append('')
        for sid in collisions:
            lines.append(f'- `{sid}`')
        lines.append('')

    if shape_problems:
        lines.append(f'### {len(shape_problems)} shape error(s)')
        lines.append('')
        for sid, errs in shape_problems.items():
            lines.append(f'- `{sid}`: ' + '; '.join(errs))
        lines.append('')

    if duplicates:
        lines.append(f'<details>')
        lines.append(
            f'<summary>{len(duplicates)} candidate(s) flagged as possible duplicates '
            f'(cosine similarity ≥ threshold against an existing ILI)</summary>')
        lines.append('')
        lines.append('| New ID | Proposed definition | Similarity | Existing ID | Existing definition |')
        lines.append('|---|---|---|---|---|')
        for sid, (match_id, match_text, score) in sorted(duplicates.items(), key=lambda kv: -kv[1][2]):
            new_defn = str(head_entries[sid]['definition'])
            lines.append(f'| `{sid}` | "{new_defn}" | {score:.3f} | `{match_id}` | "{match_text}" |')
        lines.append('')
        lines.append('</details>')
        lines.append('')

    clean_count = len(added_ids) - len(shape_problems) - len(duplicates)
    if clean_count > 0:
        lines.append(f'The remaining {clean_count} candidate(s) passed all diff-checkable validation with no flags.')
        lines.append('')

    lines.append(
        'This is advisory, not blocking - a high similarity score is a prompt for reviewer '
        'judgment, not proof of duplication. Some checks the contributor\'s local `propose-ili.py` '
        'run performs (structural WN-LMF checks, the English-language heuristic, and in-submission '
        'duplicate detection) require the original wordnet file and cannot be re-run here - see the '
        'PR description\'s QC report for those. See [PROPOSING_ILIS.md](PROPOSING_ILIS.md) for '
        'details.')
    lines.append('')
    lines.append('*Posted automatically on push. Re-runs replace this comment.*')
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Generate the CI validation comment for an ILI-proposal pull request.')
    parser.add_argument('--base-ili', type=Path, required=True,
                         help="ili.ttl as it exists on the PR's target branch")
    parser.add_argument('--head-ili', type=Path, default=Path('ili.ttl'),
                         help="ili.ttl as it exists on the PR's own branch (default: ./ili.ttl)")
    parser.add_argument('--diff', type=Path, required=True,
                         help='a `git diff` of ili.ttl between the target branch and this PR')
    parser.add_argument('--output', type=Path, default=None,
                         help='write the comment here (default: stdout)')
    parser.add_argument('--similarity-threshold', type=float, default=DEFAULT_SIMILARITY_THRESHOLD)
    args = parser.parse_args()

    base_entries = load_entries(args.base_ili)
    head_entries = load_entries(args.head_ili)

    added_ids, removed_other_content = added_ids_from_diff(args.diff.read_text())
    added_ids = [sid for sid in added_ids if sid in head_entries]  # defensive: only known subjects

    collisions = [sid for sid in added_ids if sid in base_entries]
    non_colliding = [sid for sid in added_ids if sid not in base_entries]

    shape_problems = {}
    for sid in non_colliding:
        errors = shape_errors_for(head_entries[sid])
        if errors:
            shape_problems[sid] = errors

    duplicates = find_duplicates(non_colliding, head_entries, base_entries, args.similarity_threshold)

    comment = render_comment(
        added_ids, head_entries, base_entries, shape_problems, collisions,
        removed_other_content, duplicates)

    if args.output:
        args.output.write_text(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
