# ILI Status Vocabulary

This document specifies the vocabulary for annotating the status of an ILI
concept, as discussed in [#8](https://github.com/globalwordnet/cili/issues/8).
It answers the two questions raised there: what the possible statuses are,
and how they should be encoded in `ili.ttl`.

The vocabulary terms below (`ili:status`, `ili:supersededBy`, and the status
values) are formally defined, as OWL classes/properties/individuals, in
[`ontology.xml`](ontology.xml), which resolves at
<https://globalwordnet.github.io/cili/ontology.xml>.

This is a specification for the vocabulary only. Applying it to real data
(marking specific concepts as `provisional` or `deprecated`, and generating
`cili.tsv`/HTML output that reflects it) is separate follow-up work, not
covered by this document.

## Status values

Every ILI concept has one of the following statuses:

* `active` — accepted and in current use. This is the default: a concept
  with no `ili:status` triple is `active`.
* `provisional` — proposed via a wordnet upload (e.g. `ili="in"` in
  WN-LMF) but not yet confirmed. Per the discussion on #8 and #5, OMW grants
  new concepts this status for roughly a month before they're accepted or
  the wordnet that proposed them is rejected.
* `deprecated` — no longer recommended for use. A deprecated concept
  should normally be accompanied by one or more `ili:supersededBy` links
  (see below). The ID itself is retained rather than deleted, so it is
  never recycled.

This mirrors the vocabulary sketched by @goodmami in [#8](https://github.com/globalwordnet/cili/issues/8#issuecomment-772989751),
with `provisional` in place of the earlier "proposed" terminology from #5.

`removed` was considered in the original issue as a further state beyond
`deprecated` (for concepts whose description is cleared entirely) but was
not adopted here — per the issue's own preference for simplicity, a single
`deprecated` status is enough unless a concrete need for `removed` arises.

## Properties

### `ili:status`

Takes one of the three values above. Absence of this property means
`active`.

### `ili:supersededBy`

Links a `deprecated` concept to the concept(s) that replace it. May be
repeated on the same subject to represent a split into multiple concepts
(per @fcbond's note in [#8](https://github.com/globalwordnet/cili/issues/8#issuecomment-2459007859)
that a split is expressed as a deprecation with multiple `supersededBy`
targets, rather than as a separate relation).

### `dc:description`

Already used elsewhere in `ili.ttl` for concept definitions; reused here,
on a `deprecated` concept, as an optional free-text note explaining why it
was deprecated or split — per @fcbond's suggestion in
[#8](https://github.com/globalwordnet/cili/issues/8#issuecomment-2459007859)
that `dc:description` is the nearest existing Dublin Core term for this,
in the absence of a better-fitting one.

## Namespace

Concept IDs and vocabulary terms live in two separate namespaces, resolved
by two separate `ili.ttl` prefix declarations:

```turtle
@prefix ili: <https://globalwordnet.github.io/cili/ontology.xml#> .
@base <http://globalwordnet.org/cili/> .
```

* Concept IDs (`<i123>`, and the existing `<Concept>`/`<Instance>` classes)
  stay exactly as they are today, relative to `@base`, i.e.
  `http://globalwordnet.org/cili/i123`. Nothing about any existing concept's
  URI changes.
* The new vocabulary terms — `ili:status`, `ili:supersededBy`, and the
  status values `ili:provisional`/`ili:active`/`ili:deprecated` — are
  prefixed with `ili:`, which now points at
  `https://globalwordnet.github.io/cili/ontology.xml#`, a real,
  dereferenceable document ([`ontology.xml`](ontology.xml), published via
  GitHub Pages), rather than `http://globalwordnet.org/cili/`, which does
  not currently resolve.

This also settles the namespace-collision concern @goodmami raised in
[#8](https://github.com/globalwordnet/cili/issues/8#issuecomment-929587590):
rather than defining vocabulary terms in the same namespace as concept
identifiers (as `<Concept>`/`<Instance>` currently are), they now live in a
genuinely distinct, resolving namespace, with no change required to any
existing concept URI.

`make-html.py`'s existing `ILI.status` lookup (it already rendered a
"Status" field, defaulting to `active`, in anticipation of this vocabulary)
has been updated to read `ili:status` from the new namespace instead, and
copies `ontology.xml` into the generated site so it keeps resolving there
after every `make-html.py` run.

## Example

The IDs below are placeholders, not references to real ILI concepts:

```turtle
@prefix ili: <https://globalwordnet.github.io/cili/ontology.xml#> .
@base <http://globalwordnet.org/cili/> .

<iXXXXX> a <Concept> ;
    skos:definition "..."@en ;
    dc:source pwn30:00020997-r ;
    ili:status ili:deprecated ;
    ili:supersededBy <iYYYYY> ;
    dc:description "merged into a synonymous concept" .

<iZZZZZ> a <Concept> ;
    skos:definition "..."@en ;
    dc:source pwn31:02451912-n ;
    ili:status ili:provisional .
```

(The general shape follows @goodmami's original sketch in
[#8](https://github.com/globalwordnet/cili/issues/8#issuecomment-772989751),
which used two real concepts purely to illustrate the syntax.)
