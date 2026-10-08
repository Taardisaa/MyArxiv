"""Collect a bounded, deduplicated GPU-security feed from the arXiv Atom API."""
import datetime as dt
import json
import pathlib
import re
import time
import tomllib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
NS = {'a': 'http://www.w3.org/2005/Atom', 'x': 'http://arxiv.org/schemas/atom'}
GPU = re.compile(r'\b(?:gpus?|cuda|graphics processing)\b', re.I)
SEC = re.compile(r'side[- ]channels?|rowhammer|confidential|trusted execution|memory safety|information flow|data isolation|fault attacks?', re.I)

def relevant(title, abstract):
    # Require the GPU and a concrete security concept together in the title
    # or one abstract sentence, rather than GPU acceleration anywhere in a paper.
    if GPU.search(title) and (SEC.search(title) or re.search(r'\bsecurity\b', title, re.I)):
        return True
    if not GPU.search(title) and len(GPU.findall(abstract)) < 2:
        return False
    return any(GPU.search(s) and SEC.search(s) for s in re.split(r'(?<=[.!?])\s+', abstract))

def collect(xml_path=None):
    scope = tomllib.loads((ROOT/'scope.toml').read_text())
    def expression(terms):
        return '(' + ' OR '.join(f'{field}:"{term}"' for term in terms for field in ['ti','abs']) + ')'
    query = expression(scope['gpu_terms']) + ' AND ' + expression(scope['security_terms'])
    if xml_path:
        body = pathlib.Path(xml_path).read_bytes()
    else:
        url = 'https://export.arxiv.org/api/query?' + urllib.parse.urlencode({'search_query': query, 'start': 0, 'max_results': scope['fetch_limit'], 'sortBy':'lastUpdatedDate','sortOrder':'descending'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'MyArxiv-personal-reader/2.0'}),timeout=40) as response:
                    body = response.read()
                feed = ET.fromstring(body)
                if feed.tag != '{http://www.w3.org/2005/Atom}feed':
                    raise ValueError('arXiv returned a non-Atom response')
                break
            except Exception:
                if attempt == 2: raise
                time.sleep(4 * (attempt+1))
    feed = ET.fromstring(body)
    if feed.find('.//a:entry/a:id', NS) is not None and 'api/errors' in feed.findtext('.//a:entry/a:id', '', NS):
        raise ValueError('arXiv API rejected the query')
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=scope['retention_days'])
    unique = {}
    for e in feed.findall('a:entry',NS):
        def text(name):return ' '.join(e.findtext('a:'+name,'',NS).split())
        title, summary, updated, published, identifier = [text(n) for n in ['title','summary','updated','published','id']]
        if dt.datetime.fromisoformat(updated.replace('Z','+00:00')) < cutoff or not relevant(title, summary): continue
        identifier = identifier.replace('http://','https://')
        base = re.sub(r'v\d+$','',identifier)
        pdf = next((l.attrib['href'].replace('http://','https://') for l in e.findall('a:link',NS) if l.get('title')=='pdf'),identifier.replace('/abs/','/pdf/'))
        paper = dict(id=identifier,updated=updated,published=published,title=title,summary=summary,authors=[a.findtext('a:name','',NS) for a in e.findall('a:author',NS)],pdf_url=pdf,comment=e.findtext('x:comment',None,NS))
        if base not in unique or unique[base]['updated'] < updated: unique[base] = paper
    cache = {}
    for p in sorted(unique.values(),key=lambda p:p['updated'],reverse=True)[:scope['max_papers']]:
        date = p['updated'][:10]+'T00:00:00Z'
        cache.setdefault(date,{}).setdefault(scope['name'],[]).append(p)
    return cache

if __name__ == '__main__':
    import sys
    data=collect(sys.argv[1] if len(sys.argv)>1 else None)
    (ROOT/'target').mkdir(exist_ok=True)
    (ROOT/'target/cache.json').write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False))
    print(f'Collected {sum(len(p) for g in data.values() for p in g.values())} GPU-security papers')
