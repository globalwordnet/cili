#!/usr/bin/env python3

"""
Script to convert a tab-separated alignment file to a Turtle file.

Requirements:
    - Python 3.6+
    - WN
Usage:
    python tab-to-ttl.py ALIGNMENT.TSV WN_ID WN_URL > ALIGNMENT.TTL
Example:
    python tab-to-ttl.py ili-map-pwn31.tab pwn31 http://wordnet-rdf.princeton.edu/wn31/ > ili-map-wn31.ttl
"""

import sys
import wn

if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit('usage: python tab-to-ttl.py ALIGNMENT.TSV WN_ID WN_URL')
    wn_id = sys.argv[2]
    wn_url = sys.argv[3]

    if wn_id == "pwn30":
        wordnet = wn.Wordnet('omw-en:1.4')
        id_prefix = "omw-en-"  # for the Princeton WordNet 3.0
    elif wn_id == "pwn31":
        wordnet = wn.Wordnet('omw-en31:1.4')
        id_prefix = "omw-en31-"  # for the Princeton WordNet 3.1
    else:
        wordnet = wn.Wordnet(wn_id)
        id_prefix = wn_id + "-"  # for other WordNets

    print("@prefix owl:    <http://www.w3.org/2002/07/owl#> .")
    print(f"@prefix {wn_id}: <{wn_url}> .")
    print("@prefix ili: <http://globalwordnet.org/ili/> .")
    print("@prefix skos: <http://www.w3.org/2004/02/skos/core#> .")
    print()

    with open(sys.argv[1]) as f:
        for line in f:
            ili, wn = line.strip().split('\t')
            synset = wordnet.synset(id_prefix + wn)
            if wn_id == "pwn31":
                if synset.pos == "n":
                    pos = "1"
                elif synset.pos == "v":
                    pos = "2"
                elif synset.pos == "a" or synset.pos == "s":
                    pos = "3"
                elif synset.pos == "r":
                    pos = "4"
                else:
                    pos = synset.pos
            else:
                pos = ""
            lemmas = [lemma.replace(" ", "_") for lemma in synset.lemmas()]
            print(f'ili:{ili} owl:sameAs {wn_id}:{pos}{wn} . # {", ".join(lemmas)}')
