#!/usr/bin/env python3

"""
Script to produce a TSV file for a release of CILI.

The mappings to the Princeton WordNet generally don't need to be
released regularly as they are unlikely to change and are already
included in WN-LMF releases of the PWN, so this script reduces the
ili.ttl file to a two-column tab-separated-value file containing only
the ILI inventory and their definitions. This assumes that every ILI
has a definition, which is true by design. The resulting .tsv file is
less than half the size of the .ttl file when uncompressed, but
roughly the same size when compressed. TSV is generally much faster to
parse, however, and doesn't require an RDF library, so it is more
appealing for downstream applications.

Requirements:
    - Python 3.6+
    - rdflib
Usage:
    python3 make-tsv.py > cili.tsv

"""

import sys

from rdflib import Graph
from rdflib.namespace import SKOS


g = Graph()
g.parse("ili.ttl", format='ttl')

# pair each ILI (ignoring the URL part) with its definition
data = [(subj.rpartition('/')[2], obj)
        for subj, obj
        in g.subject_objects(predicate=SKOS.definition)]

# sort by ILI number
data.sort(key=lambda pair: int(pair[0].lstrip('i')))

print('ILI\tDefinition')
for ili, definition in data:
    print(f'{ili}\t{definition}')

