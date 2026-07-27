#!/usr/bin/env python3

"""
Script to extract candidate ILI concepts from a WN-LMF wordnet file.

Reads a wordnet's ili="in" synsets (i.e. synsets whose author has
proposed them for a new ILI, per the WN-LMF spec), quality-checks them,
allocates new sequential ILI identifiers, and writes a Turtle fragment
in ili.ttl's existing style, ready to be appended to ili.ttl and opened
as a pull request. Also writes a QC report meant to be pasted into that
PR's description.

See PROPOSING_ILIS.md for the full proposal workflow this script is
part of (issue #9). This script does not touch git or GitHub; append
its output to ili.ttl, commit, and open the PR yourself.

Requirements:
    - Python 3.6+
    - rdflib
    - wn
    - sentence-transformers
Usage:
    python3 propose-ili.py WORDNET.xml WN_ID WN_URL > proposed.ttl
Example:
    python3 propose-ili.py oewn-2024.xml oewn http://en-word.net/id/ > proposed.ttl

"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rdflib import Graph
from rdflib.namespace import SKOS

import wn.lmf
import wn.validate

MIN_DEFINITION_LENGTH = 10
MAX_DEFINITION_LENGTH = 500
DEFAULT_SIMILARITY_THRESHOLD = 0.95
MINILM_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'

# wn.validate check codes we run against the submitted file. See
# https://wn.readthedocs.io/en/latest/api/wn.validate.html for what each
# one means; the subset picked here is the part of goodmami's requested
# "first-pass quality control" that wn.validate already implements.
STRUCTURAL_CHECKS = ('E101', 'W301', 'W302', 'W303', 'W304', 'W305', 'W306', 'W307')

# Checks that mean we can't safely turn the candidate into an ILI at all.
HARD_FAIL_CODES = {'E101', 'W303'}

# A deliberately simple, non-authoritative heuristic: ILIDefinition
# elements carry no language attribute (unlike regular Definitions), so
# this can only ever be a hint for a maintainer to double-check, never a
# hard-fail.
_COMMON_ENGLISH_WORDS = {
    'a', 'an', 'the', 'of', 'to', 'in', 'is', 'are', 'that', 'or', 'for',
    'and', 'with', 'as', 'by', 'on', 'not', 'at', 'from', 'be', 'having',
    'used', 'one', 'who', 'which', 'this',
}


class Candidate:
    def __init__(self, synset_id: str, definition: str, is_instance: bool):
        self.synset_id = synset_id
        self.definition = definition
        self.is_instance = is_instance
        self.warnings: List[str] = []
        self.hard_fails: List[str] = []
        self.assigned_id: Optional[str] = None

    @property
    def accepted(self) -> bool:
        return not self.hard_fails


def load_ili_ids_and_definitions(ili_file: Path) -> Tuple[Set[str], List[Tuple[str, str]]]:
    g = Graph()
    g.parse(ili_file, format='ttl')
    ids = set()
    definitions = []
    for subj, obj in g.subject_objects(predicate=SKOS.definition):
        ili = subj.rpartition('/')[2]
        ids.add(ili)
        definitions.append((ili, str(obj)))
    return ids, definitions


def next_id_after(ids: Set[str]) -> int:
    if not ids:
        return 1
    return max(int(i.lstrip('i')) for i in ids) + 1


def looks_english(text: str) -> bool:
    words = re.findall(r"[a-zA-Z']+", text.lower())
    if not words:
        return False
    ascii_ratio = sum(c.isascii() for c in text) / len(text)
    has_common_word = any(w in _COMMON_ENGLISH_WORDS for w in words)
    return ascii_ratio > 0.9 and has_common_word


def escape_turtle_string(text: str) -> str:
    text = ' '.join(text.split())  # collapse whitespace/newlines to a single line
    text = text.replace('\\', '\\\\').replace('"', '\\"')
    return text


def is_instance_synset(synset: wn.lmf.Synset) -> bool:
    return any(r.get('relType') == 'instance_hypernym' for r in synset.get('relations', []))


def extract_candidates(lex: wn.lmf.Lexicon) -> List[Candidate]:
    candidates = []
    for ss in lex.get('synsets', []):
        if ss.get('ili') != 'in':
            continue
        ili_definition = ss.get('ili_definition')
        definition = ili_definition['text'].strip() if ili_definition else ''
        candidates.append(Candidate(ss['id'], definition, is_instance_synset(ss)))
    return candidates


def apply_structural_checks(lex: wn.lmf.Lexicon, candidates: List[Candidate]) -> None:
    by_id = {c.synset_id: c for c in candidates}
    report = wn.validate.validate(lex, select=STRUCTURAL_CHECKS, progress_handler=None)
    for code in STRUCTURAL_CHECKS:
        check = report.get(code)
        if not check:
            continue
        for synset_id in check['items']:
            candidate = by_id.get(synset_id)
            if candidate is None:
                continue
            message = f'{code}: {check["message"]}'
            if code in HARD_FAIL_CODES:
                candidate.hard_fails.append(message)
            else:
                candidate.warnings.append(message)


def apply_length_check(candidates: List[Candidate]) -> None:
    for candidate in candidates:
        if candidate.hard_fails:
            continue  # already unusable (e.g. missing definition entirely)
        length = len(candidate.definition)
        if length < MIN_DEFINITION_LENGTH or length > MAX_DEFINITION_LENGTH:
            candidate.hard_fails.append(
                f'definition length ({length} chars) outside the expected '
                f'{MIN_DEFINITION_LENGTH}-{MAX_DEFINITION_LENGTH} character range')


def apply_english_heuristic(candidates: List[Candidate]) -> None:
    for candidate in candidates:
        if candidate.hard_fails:
            continue
        if not looks_english(candidate.definition):
            candidate.warnings.append(
                'definition does not look like English (heuristic check, may be a false positive)')


def apply_similarity_check(
    candidates: List[Candidate],
    existing_definitions: List[Tuple[str, str]],
    threshold: float,
) -> None:
    checkable = [c for c in candidates if not c.hard_fails]
    if not checkable or not existing_definitions:
        return

    from sentence_transformers import SentenceTransformer, util

    model = SentenceTransformer(MINILM_MODEL)
    existing_ilis = [ili for ili, _ in existing_definitions]
    existing_texts = [text for _, text in existing_definitions]
    existing_embeddings = model.encode(
        existing_texts, normalize_embeddings=True, convert_to_tensor=True, show_progress_bar=False)
    candidate_embeddings = model.encode(
        [c.definition for c in checkable], normalize_embeddings=True,
        convert_to_tensor=True, show_progress_bar=False)

    scores = util.cos_sim(candidate_embeddings, existing_embeddings)
    for candidate, row in zip(checkable, scores):
        best_score, best_index = float(row.max()), int(row.argmax())
        if best_score >= threshold:
            matched_ili = existing_ilis[best_index]
            matched_text = existing_texts[best_index]
            candidate.warnings.append(
                f'possible duplicate of <{matched_ili}> (cosine similarity '
                f'{best_score:.3f}): "{matched_text}"')


def assign_ids(candidates: List[Candidate], next_id: int) -> None:
    for candidate in candidates:
        if candidate.accepted:
            candidate.assigned_id = f'i{next_id}'
            next_id += 1


def render_fragment(candidates: List[Candidate], wn_url: str) -> str:
    blocks = []
    for candidate in candidates:
        if not candidate.accepted:
            continue
        rdf_type = '<Instance>' if candidate.is_instance else '<Concept>'
        definition = escape_turtle_string(candidate.definition)
        source = f'{wn_url}{candidate.synset_id}'
        blocks.append(
            f'<{candidate.assigned_id}>\ta\t{rdf_type} ;\n'
            f'\tskos:definition\t"{definition}"@en ;\n'
            f'\tdc:source\t<{source}> ;\n'
            f'\tili:status\tili:provisional .\n')
    return '\n'.join(blocks)


def render_report(candidates: List[Candidate], source_name: str) -> str:
    accepted = [c for c in candidates if c.accepted]
    failed = [c for c in candidates if not c.accepted]
    lines = [
        f'# ILI proposal report for {source_name}',
        '',
        f'{len(candidates)} candidate(s) found: {len(accepted)} accepted, '
        f'{len(failed)} hard-failed.',
        '',
    ]
    if accepted:
        lines.append('## Accepted')
        for c in accepted:
            lines.append(f'- {c.assigned_id} (was {c.synset_id}): "{c.definition}"')
            for warning in c.warnings:
                lines.append(f'  - warning: {warning}')
        lines.append('')
    if failed:
        lines.append('## Hard-failed (not included in the fragment)')
        for c in failed:
            lines.append(f'- {c.synset_id}: "{c.definition}"')
            for reason in c.hard_fails:
                lines.append(f'  - {reason}')
        lines.append('')
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Extract ILI candidates from a WN-LMF file into an ili.ttl-ready fragment.')
    parser.add_argument('wordnet', type=Path, help='WN-LMF XML file to read')
    parser.add_argument('wn_id', help='short id for the source wordnet, e.g. oewn')
    parser.add_argument(
        'wn_url', help='base URL used to build each dc:source IRI (synset id is appended), '
                        'e.g. http://en-word.net/id/')
    parser.add_argument('--ili-file', type=Path, default=Path('ili.ttl'),
                         help='path to the current ili.ttl (default: ./ili.ttl)')
    parser.add_argument('--report', type=Path, default=None,
                         help='write the QC report here instead of stderr')
    parser.add_argument('--similarity-threshold', type=float, default=DEFAULT_SIMILARITY_THRESHOLD,
                         help='cosine similarity (0-1) above which an existing definition is '
                              f'flagged as a possible duplicate (default: {DEFAULT_SIMILARITY_THRESHOLD})')
    args = parser.parse_args()

    try:
        resource = wn.lmf.load(args.wordnet)
    except wn.lmf.LMFError as exc:
        sys.exit(f'{args.wordnet}: invalid WN-LMF file: {exc}')

    lexicons = resource.get('lexicons', [])
    if not lexicons:
        sys.exit(f'{args.wordnet}: no lexicons found')
    if len(lexicons) > 1:
        print(f'note: {args.wordnet} contains {len(lexicons)} lexicons; '
              'only the first is processed', file=sys.stderr)
    lex = lexicons[0]

    existing_ids, existing_definitions = load_ili_ids_and_definitions(args.ili_file)
    next_id = next_id_after(existing_ids)

    candidates = extract_candidates(lex)
    if not candidates:
        print(f'no ili="in" synsets found in {args.wordnet}', file=sys.stderr)
        return

    apply_structural_checks(lex, candidates)
    apply_length_check(candidates)
    apply_english_heuristic(candidates)
    apply_similarity_check(candidates, existing_definitions, args.similarity_threshold)
    assign_ids(candidates, next_id)

    fragment = render_fragment(candidates, args.wn_url)
    if fragment:
        print(fragment)

    report = render_report(candidates, args.wordnet.name)
    if args.report:
        args.report.write_text(report)
    else:
        print(report, file=sys.stderr)


if __name__ == '__main__':
    main()
