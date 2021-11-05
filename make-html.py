#!/usr/bin/env python3

"""
Requirements:
    - Python 3.6+
    - rdflib
Usage:
    python3 make-html.py OUTDIR

"""

from typing import Dict
import sys
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import RDF, DC, SKOS, Namespace

if len(sys.argv) != 2:
    sys.exit('usage: python3 make-html.py OUTDIR')
OUTDIR = Path(sys.argv[1])
if OUTDIR.exists():
    sys.exit(f'{OUTDIR!s} already exists; remove or rename it, then try again')
OUTDIR.mkdir()

css = '''\
:root {
  --text-color: #111;
  --background-color: white;
}

body {
    width: 100%;
    color: var(--text-color);
    margin: 0;
    background-color: var(--background-color);
    font-family: "Roboto", "Fira Sans", sans-serif;
}
header {
    width: 100%;
    margin: 0;
    padding: 10px;
    background-color: black;
    color: #eee;
}
header h1 { margin-top: 0; text-align: center; }
article {
    width: 800px;
    margin: 10px auto;
    padding: 10px;
    border-radius: 10px;
}
article.ili { background-color: rgba(128,128,128,.1); }
article footer {
    margin: 10px;
    text-align: right;
}

blockquote {
    margin: 10px 0;
    padding: 10px;
    border-left: 4px solid #888;
    background-color: rgba(128,128,128,.1)
}

dl {
    display: grid;
    grid-template-columns: max-content auto;
}
dt { grid-column-start: 1; }
dd { grid-column-start: 2; }

.ili-type, dd { font-weight: bold; }
a { color: rgb(90, 170, 255); text-decoration: none; }
a:hover { text-decoration: underline; }
a:active { color: rgb(120, 200, 255); }


@media screen and (max-width: 799px) {
    article {
        width: 400px;
    }
}

@media (prefers-color-scheme: dark) {
    body {
        --text-color: #eee;
        --background-color: black;
    }
}
'''

base = '''\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <link href="_static/style.css" rel="stylesheet">
  <title>{title}</title>
</head>
<body>
  <header>
    <h1>Global WordNet Association: Interlingual Index</h1>
  </header>

{content}

</body>
</html>

'''

article = '''\
  <article class="ili" itemscope itemtype="{type!s}" itemid="{subject!s}">
    <h1>{ili}</h1>

    <div class="ili-type">{short_type!s}</div>

    <blockquote itemprop="http://www.w3.org/2004/02/skos/core#definition">
    {definition!s}
    </blockquote>

    <dl>
      <dt>Status</dt>
      <dd itemprop="status">{status!s}</dd>
      <dt>Source</dt>
      <dd><a href="{source_info[url]}">{source_info[name]}</a>
          &ndash;
          <a itemprop="http://purl.org/dc/elements/1.1/source" href="{source!s}">{source_info[local]}</a>
      </dd>
    </dl>

    <footer>Part of <a href="https://github.com/globalwordnet/cili/">globalwordnet/cili</a></footer>
  </article>
'''

ILI = Namespace('http://globalwordnet.org/ili/')

sources = {
    'http://wordnet-rdf.princeton.edu/wn30/': ('Princeton WordNet 3.0',
                                               'https://wordnet.princeton.edu/'),
}


def source_info(url: str) -> Dict[str, str]:
    for src in sources:
        if url.startswith(src):
            local = url.removeprefix(src).lstrip('/#')
            name, project_url = sources[src]
            return {'name': name, 'url': project_url, 'local': local}
    raise LookupError(f'source info not found for {url!s}')


def short_name(s: str) -> str:
    return s.rpartition('/')[2]


g = Graph()
g.parse("ili.ttl", format='ttl')

for subj in g.subjects():
    type = g.value(subject=subj, predicate=RDF.type)
    if type not in (ILI.Concept, ILI.Instance):
        continue
    ili = short_name(subj)
    source = g.value(subject=subj, predicate=DC.source)
    data = {
        'ili': ili,
        'subject': subj,
        'type': type,
        'short_type': short_name(type),
        'definition': g.value(subject=subj, predicate=SKOS.definition),
        'status': g.value(subject=subj, predicate=ILI.status, default='active'),
        'source': source,
        'source_info': source_info(source),
    }
    content = base.format(title=f'ILI: {ili}', content=article.format(**data))
    (OUTDIR / f'{ili}.html').write_text(content)

(OUTDIR / '.nojekyll').touch()  # for GitHub pages
(OUTDIR / '_static').mkdir()
(OUTDIR / '_static' / 'style.css').write_text(css)
(OUTDIR / 'index.html').write_text(base.format(
    title='Interlingual Index',
    content='''\
  <article>
    <a href="https://github.com/globalwordnet/cili">https://github.com/globalwordnet/cili</a>
  </article>
'''))
