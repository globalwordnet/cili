# Sense mappings

WordNets provide two types of IDs:
- synset IDs (in Princeton WordNet, a number followed by `-n` for noun, `-v` for verbs, etc.)
- sense IDs (in Princeton WordNet, a lemma followed by a number of `:`-separated numerical and lexical IDs)

Synsets represent sets of synonyms (i.e., abstract concepts). Senses represent possible meanings that a lexeme can take. A word sense thus corresponds to a tuple of synset and lemma (a lexicalization for a specific synset, a meaning of a specific lexeme).

ILI provides a mapping between synset IDs, only, but not to sense IDs. For convenience, we provide a mapping of synset IDs to sense IDs extracted from a number of WordNets. Note, that the synset IDs are not ILI ids, but in combination with other mapping files in this repository, they can be used to map ILIs to resource-specific sense IDs.

The purpose of the provided mapping is that corpora with WordNet *sense* (but not *synset*) annotations, e.g., [SemCor](https://web.eecs.umich.edu/~mihalcea/downloads.html#semcor) can be directly processed along with other ILI-linked resources, without having to use the original software.

These mappings are automatically extracted from WordNet dict files, to re-build them, run

	$> make

We do not provide an RDF version. However, note that the TAB files can be directly SPARQLed with [TARQL](https://github.com/tarql/tarql) and combined with other RDF data using [Fintan](https://github.com/Pret-a-LLOD/Fintan).

# Known issues

- currently limited to Princeton WordNet
- support for `-s` synsets is incomplete, we generate substrings for these (compare with `startswith`).
