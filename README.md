# Collaborative Interlingual Index

The collaborative interlingual index maintains the data for a single interlingual
index of concept for wordnets. This respository contains all the data that is
available in the Interlingual Index as well as mappings to other resources.

The following files are in this repository:

* `ili.ttl`: The main interlingual index file, containing a definition and a 
    source for each identifier. This file is in the Turtle RDF format.
* `ili-map.ttl`, `ili-map-wn30.ttl`: These two files contain the mapping from
    Princeton WordNet 3.0 to the ILI in Turtle. These files are identical
* `ili-map-pwn30.tab`: The mapping from Princeton WordNet 3.0 to the ILI as
    tab-separated values.
* `ili-map-pwn31.tab`, `ili-map-wn31.ttl`: The mappings from Princeton WordNet 3.1
    to the ILI
* `ili-map-odwn13.ttl`: The mapping from Open Dutch WordNet 1.3 to the ILI.
* `older-wn-mappings`: Automatically constructed mappings from previous versions
    of WordNet to the ILI

