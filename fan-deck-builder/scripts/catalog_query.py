#!/usr/bin/env python3
"""Query the Fanatics Collectibles slide catalog (Airtable) with the retrieval ladder.

Usage:
  python3 catalog_query.py --keywords "world cup" spain --limit 40
  python3 catalog_query.py --sport soccer --category "Athlete Partnerships"
  python3 catalog_query.py --deck DECK-070                # full deck listing
  python3 catalog_query.py --keywords madrid --thumbs ./thumbs --json out.json

Auth: AIRTABLE_PAT env var, or ~/.config/fanatics-collectibles/airtable_token.txt
(read-only data.records:read token). Never prints the token.

Output: one line per slide, canonical-dedupe applied (non-canonical dupes are
marked [dup]); freshest Data As Of first. --json writes full records; --thumbs
downloads slide thumbnails as <Slide ID>.png for visual QA (ALWAYS look at a
slide before shipping it).
"""
import json, os, pathlib, sys, urllib.parse, urllib.request

BASE, SLIDES = 'appFMMGAw98cxrGHz', 'tblJQ1ddoKy2Zi2mM'
FIELDS = ['Slide ID', 'Deck ID', 'Title Text', 'Category', 'Subcategory', 'Summary',
          'Sport(s)', 'Key Figures', 'Data As Of', 'Source File Name',
          'Dupe Group', 'Dupe Canonical', 'Slide Thumbnail']


def token():
    t = os.environ.get('AIRTABLE_PAT')
    if t:
        return t.strip()
    p = pathlib.Path.home() / '.config/fanatics-collectibles/airtable_token.txt'
    if p.exists():
        return p.read_text().strip()
    sys.exit('No Airtable token: set AIRTABLE_PAT or create ' + str(p))


def fetch(formula):
    out, offset = [], None
    while True:
        params = [('filterByFormula', formula), ('pageSize', '100')] + [('fields[]', f) for f in FIELDS]
        if offset:
            params.append(('offset', offset))
        url = f'https://api.airtable.com/v0/{BASE}/{SLIDES}?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token()}'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        out += data.get('records', [])
        offset = data.get('offset')
        if not offset:
            return out


def esc(s):
    return s.replace("'", "\\'").lower()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--keywords', nargs='*', default=[], help='searched in Body Text + Summary + Title Text + Key Figures (OR)')
    ap.add_argument('--sport', help='substring match on Sport(s), e.g. soccer')
    ap.add_argument('--category', help='exact Category')
    ap.add_argument('--deck', help='exact Deck ID, e.g. DECK-070')
    ap.add_argument('--limit', type=int, default=60)
    ap.add_argument('--all', action='store_true', help='include non-canonical duplicates')
    ap.add_argument('--json', help='write full records to this path')
    ap.add_argument('--thumbs', help='download thumbnails into this directory')
    a = ap.parse_args()

    clauses = []
    for kw in a.keywords:
        k = esc(kw)
        clauses.append(f"FIND('{k}', LOWER({{Body Text}}&' '&{{Summary}}&' '&{{Title Text}}&' '&{{Key Figures}}))>0")
    kw_part = ('OR(' + ','.join(clauses) + ')') if len(clauses) > 1 else (clauses[0] if clauses else None)
    ands = [c for c in [kw_part] if c]
    if a.sport:
        ands.append(f"FIND('{esc(a.sport)}', LOWER(ARRAYJOIN({{Sport(s)}})))>0")
    if a.category:
        ands.append(f"{{Category}}='{a.category}'")
    if a.deck:
        ands.append(f"{{Deck ID}}='{a.deck}'")
    if not ands:
        sys.exit('give at least one of --keywords/--sport/--category/--deck')
    formula = ('AND(' + ','.join(ands) + ')') if len(ands) > 1 else ands[0]

    recs = fetch(formula)
    rows = []
    for r in recs:
        f = r['fields']
        sid = f.get('Slide ID')
        if not sid:
            continue
        rows.append({
            'sid': sid, 'deck': f.get('Deck ID', ''), 'title': str(f.get('Title Text', ''))[:80],
            'cat': f.get('Category', ''), 'sub': f.get('Subcategory', ''),
            'summary': str(f.get('Summary', ''))[:120], 'sport': f.get('Sport(s)', ''),
            'asof': f.get('Data As Of', '') or '', 'src': f.get('Source File Name', ''),
            'dg': f.get('Dupe Group', ''), 'canon': bool(f.get('Dupe Canonical')),
            'thumb': (f.get('Slide Thumbnail') or [{}])[0].get('url', ''),
        })
    if not a.all:
        rows = [x for x in rows if x['canon'] or not x['dg']]
    rows.sort(key=lambda x: (x['asof'], x['deck']), reverse=True)
    rows = rows[:a.limit]

    for x in rows:
        mark = 'C' if x['canon'] else ('dup' if x['dg'] else '-')
        print(f"{x['sid']} [{mark}] {x['deck']} {x['cat'][:20]}/{str(x['sub'])[:20]} asof={x['asof'] or '?'}")
        print(f"    {x['title']} | {x['summary']}")
    print(f'-- {len(rows)} slides (canonical-deduped{" off" if a.all else ""})')

    if a.json:
        json.dump(rows, open(a.json, 'w'), indent=1)
    if a.thumbs:
        os.makedirs(a.thumbs, exist_ok=True)
        for x in rows:
            if x['thumb']:
                urllib.request.urlretrieve(x['thumb'], os.path.join(a.thumbs, x['sid'] + '.png'))
        print('thumbnails ->', a.thumbs)


if __name__ == '__main__':
    main()
