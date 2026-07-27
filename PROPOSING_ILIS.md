# Proposing New ILI Concepts

This document describes how to propose new ILI concepts by opening a pull
request against `ili.ttl`, as discussed in
[#9](https://github.com/globalwordnet/cili/issues/9). It replaces the
previous informal process (a wordnet marks synsets `ili="in"`, and OMW
maintainers "scoop them up" for offline review) with an ordinary, visible
GitHub PR: a real diff, a discussion thread, and a review queue.

This covers **proposing** and **reviewing** new concepts. Once a PR
touching `ili.ttl` is opened, a GitHub Actions workflow automatically
posts a validation comment on it (see "Automated CI validation" under
"For maintainers" below); a few other items are still manual or deferred
(see "Not yet built" at the end of this document).

## For contributors

### 1. Mark your candidate synsets

In your wordnet's WN-LMF file, set `ili="in"` on each synset you're
proposing, with an `<ILIDefinition>` child giving its proposed English
gloss — this is the standard WN-LMF mechanism for an unresolved ILI
proposal, not anything CILI-specific.

### 2. Run `propose-ili.py`

```
python3 propose-ili.py WORDNET.xml WN_ID WN_URL > proposed.ttl
```

`WORDNET.xml` is your WN-LMF file. `WN_ID` is a short identifier for your
wordnet (e.g. `oewn`); `WN_URL` is a base URL used to build a `dc:source`
link for each proposed concept (your synset's local WN-LMF id is appended
to it), e.g.:

```
python3 propose-ili.py oewn-2024.xml oewn http://en-word.net/id/ > proposed.ttl
```

This requires the packages in `requirements.txt` (`pip install -r
requirements.txt`), and will download a small sentence-embedding model
(`sentence-transformers/all-MiniLM-L6-v2`, used for the duplicate check
below) the first time it runs.

**Known issue:** if this fails with `invalid or missing DOCTYPE
declaration` even though your file looks like valid WN-LMF, check for
leading whitespace before `<!DOCTYPE` on the file's second line (e.g. a
pretty-printer indented it). `wn.lmf.load` only trims trailing whitespace
from that line, not leading, so an indented DOCTYPE fails its exact-match
check. Strip the indentation from that one line and try again — this was
hit while testing against a real 3.1 wordnet export.

The script:
* Extracts every `ili="in"` synset and its proposed definition.
* Runs a battery of quality checks (see "What gets checked" below).
* Allocates each surviving candidate the next available `iNNNNN` id.
* Writes a Turtle fragment (`proposed.ttl` above) in `ili.ttl`'s existing
  style, and a QC report to stderr (use `--report FILE` to write it to a
  file instead).

Rejected candidates are **not** included in the fragment — see the report
for why.

### 3. Open the pull request

* Append `proposed.ttl` to the end of `ili.ttl` (`cat proposed.ttl >>
  ili.ttl`).
* Commit and push.
* Open a PR against `master`. **Paste the QC report into the PR
  description** — this is what a maintainer reviews against; don't just
  link to it.

### Keep proposals reasonably sized

Please don't submit a single PR proposing thousands of concepts at once.
As a rough guide, keep batches to roughly 100 candidates or so per PR. If
you have a large backlog, split it into several PRs — this keeps each PR
reviewable as an actual diff, which is the entire point of doing this
through GitHub rather than offline. Oversized PRs will be sent back to be
split up rather than reviewed as-is.

### If your PR conflicts after another proposal merges

IDs are allocated sequentially based on `ili.ttl` at the time you ran the
script. If another proposal PR merges before yours, your candidates may
have been assigned IDs that now already exist — `git` won't necessarily
flag this as a merge conflict, since both changes are pure appends. If a
maintainer flags an ID collision, just rerun `propose-ili.py` against the
latest `master` and push again; it always allocates from the current file,
so this reallocates cleanly.

## For maintainers

### What gets checked

* Structural checks from `wn`'s own WN-LMF validator (missing/blank
  definitions, non-unique ids, in-file duplicate ILIs or definitions,
  etc.) — these are effectively free correctness checks and are treated
  as hard failures.
* Definition length (10–500 characters) — hard failure outside that
  range.
* A simple heuristic flag for definitions that don't look like English —
  **warning only**, since `<ILIDefinition>` carries no language attribute
  to check against, this is a guess and can false-positive.
* A semantic duplicate check: each candidate definition is compared
  (cosine similarity via MiniLM sentence embeddings) against every
  existing `skos:definition` in `ili.ttl`, and matches above 0.95 (by
  default; contributors can adjust with `--similarity-threshold`) are
  flagged — **warning only**, not a hard failure.

  **Read this warning for what it actually is.** At MiniLM's scale, a
  0.95 threshold mostly catches near-verbatim or lightly-reworded reuse
  of an existing definition (e.g. a synonym swapped here or there) — not
  every genuine paraphrase. Two independently-written definitions of the
  same concept can easily score well below 0.95 and still be real
  duplicates. Treat a high score as a strong hint, and the absence of one
  as no guarantee of novelty — it's not a substitute for judgment,
  especially for fine-grained or closely-related senses (see the
  discussion on PR #17 for a real example of two genuinely distinct PWN
  synsets that were nearly indistinguishable by gloss alone).

Hard failures mean the candidate wasn't included in the fragment at all.
Warnings mean it *was* included, but flagged for you to look at.

### Automated CI validation

[`.github/workflows/validate-ili-proposal.yml`](.github/workflows/validate-ili-proposal.yml)
runs on every PR that touches `ili.ttl` and posts (or, on later pushes to
the same PR, updates in place) a comment summarizing the result, via
[`validate-ili-proposal.py`](validate-ili-proposal.py).

It necessarily checks *less* than the contributor's local `propose-ili.py`
run: a CI job only has the git history, not the contributor's original
WN-LMF file, so it can't re-run the structural WN-LMF checks or the
English-language heuristic. What it does check, using only `ili.ttl`
before and after the PR:

* **Shape** of every newly-added concept (correct `a <Concept>`/
  `<Instance>`, an `@en`-tagged `skos:definition`, `dc:source`,
  `ili:status ili:provisional`).
* **ID collisions** — an added id that already exists on the target
  branch, most likely because another proposal PR merged first.
* **The same semantic duplicate check** propose-ili.py runs locally,
  re-run against whatever is currently on the target branch (so it stays
  accurate even if other proposals merged since the contributor last ran
  the script).
* Whether the diff **removes or modifies existing lines**, not just
  appends new ones — flagged for a closer look, since a proposal PR
  should normally be a pure append.

It's advisory, not blocking — there's no branch protection requiring it
to pass. Treat the comment the same way as the PR description's QC
report: warnings are judgment calls, collisions and shape errors are
worth resolving before merging.

### Reviewing a proposal PR

* Read the QC report in the PR description, and the CI comment once it
  posts — together they cover everything checked (see above for which
  checks run where).
* Every proposed concept should carry `ili:status ili:provisional` (see
  [VOCABULARY.md](VOCABULARY.md)) — that's expected and correct, not a
  mistake to fix before merging.
* If CI flags an ID collision, ask the contributor to rerun
  `propose-ili.py` against current `master` and push again.

### Promoting provisional concepts

Per the existing OMW process, a proposed concept is typically given
roughly a month before being confirmed. There's no automation for this
yet: periodically, grep `ili.ttl` for `ili:provisional`, review entries
past that window, and delete the `ili:status` triple to promote them
(absence of the triple means `active`, per
[VOCABULARY.md](VOCABULARY.md)).

## Not yet built

These were discussed in #9 but are deliberately out of scope for now —
tracked as follow-up work, not silently dropped:

* **Naisc-based taxonomic-neighbor comparison** (comparing a candidate's
  relations/hypernyms against similar existing concepts, not just its
  definition text) — a separate, externally-maintained tool; integrate
  once it has a stable callable interface.
* **Automated provisional → active promotion.**
* **Turning CI validation into a required/blocking check** — it's
  advisory for now; the repo has no branch protection today.
