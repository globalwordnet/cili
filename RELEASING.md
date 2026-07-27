# Release Procedure

This document describes when and how to publish a new CILI release, as
requested in [#4](https://github.com/globalwordnet/cili/issues/4).

## When to release

CILI does not follow a strict release calendar. In practice there has been a
single release, [`v1.0`](https://github.com/globalwordnet/cili/releases/tag/v1.0),
published in December 2020. A new release should be considered when:

* Mappings for a new source wordnet or wordnet version have been added (for
  example, the Princeton WordNet 3.1 mappings).
* A meaningful batch of corrections to existing mappings has accumulated on
  `master` (as opposed to a single one-off fix).
* The Open Multilingual Wordnet (OMW) needs an updated CILI snapshot to
  accompany one of its own releases.

If there is a steady trickle of small fixes, aim for roughly one release a
year rather than releasing after every merged PR. There is no need to release
on a fixed date if nothing of substance has changed since the last one.

## Pre-release checklist

* Confirm `master` is in the state you want to release: any PRs with data
  fixes intended for this release are merged, and any known-bad mappings
  reported in open issues have either been fixed or are consciously deferred.
* Regenerate the derived files locally to make sure they still build
  cleanly:

      pip install -r requirements.txt
      python3 make-tsv.py > cili.tsv

* Update the public browsing site (published from the `gh-pages` branch) so
  it matches the data on `master`:

      git checkout gh-pages
      rm -fr docs
      python make-html.py docs
      git commit -am "Update HTML for <release>"
      git push

## Creating the release

1. Choose a version tag. The only precedent is `v1.0`; use a new minor
   version (e.g. `v1.1`) for incremental corrections, or a new major version
   (e.g. `v2.0`) when the release changes the baseline wordnet version being
   mapped (as adding PWN 3.1 would).
2. On GitHub, go to **Releases → Draft a new release**, target `master`, and
   create the new tag.
3. Write release notes summarizing what changed since the previous release:
   new wordnets/versions mapped, notable corrected mappings, and any issues
   or PRs closed by this release.
4. Publish the release.

Publishing the release triggers
[`.github/workflows/release.yml`](.github/workflows/release.yml)
automatically. That workflow builds `cili.tsv`, compresses it to
`cili.tsv.xz`, and attaches it to the release as an asset — no manual asset
upload is needed.

## After the release

* Announce the release to the OMW community and/or the Global Wordnet
  Association, describing what changed.
* Update `README.md` if the set of files in the repository or their
  descriptions changed.
* File issues for any follow-up work identified while preparing the release
  (e.g. mappings still needing review) so it isn't lost before the next one.
