#!/usr/bin/env python3
"""Build the Weekend Warriors "Pray for Your Leaders" dataset.

Sources (all public, refreshed by their maintainers continuously):
  - Congress + President/VP: github.com/unitedstates/congress-legislators
  - Governors & statewide officers: github.com/openstates/people (data/*/executive)
  - State legislators: data.openstates.org/people/current/{st}.csv (Plural Open States)
  - Supreme Court: supremecourt.gov (static list in national_static.json — update when a Justice changes)

Run:  python scripts/build_data.py  (needs `people/` sparse clone next to it; see workflow)
Output: docs/data/index.json and docs/data/states/{ST}.json
"""
import csv, io, json, os, sys, datetime, glob, urllib.request
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'data')
PEOPLE = os.environ.get('PEOPLE_DIR', os.path.join(ROOT, 'people'))
TODAY = datetime.date.today().isoformat()

STATES = {
 'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware',
 'DC':'District of Columbia','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa',
 'KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota',
 'MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico',
 'NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island',
 'SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington',
 'WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming'}

EXEC_ORDER = ['governor', 'mayor', 'lieutenant governor', 'attorney general', 'secretary of state', 'treasurer', 'comptroller',
              'controller', 'auditor', 'superintendent of public instruction', 'commissioner of agriculture', 'commissioner of insurance',
              'commissioner of labor', 'public service commissioner', 'chief financial officer', 'land commissioner']
LEADER_TITLES = ['Speaker of the House', 'Senate Majority Leader', 'Senate Minority Leader', 'House Majority Leader',
                 'House Minority Leader', 'President Pro Tempore of the Senate']

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'weekend-warriors-prayer-map'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def ordinal(n):
    n = int(n)
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1:'st',2:'nd',3:'rd'}.get(n % 10, 'th')}"

def current(term_end):
    return str(term_end or '9999-12-31') >= TODAY

def main():
    os.makedirs(os.path.join(OUT, 'states'), exist_ok=True)
    leg = json.loads(get('https://unitedstates.github.io/congress-legislators/legislators-current.json'))
    exe = json.loads(get('https://unitedstates.github.io/congress-legislators/executive.json'))
    static = json.load(open(os.path.join(ROOT, 'scripts', 'national_static.json')))

    # ---- National (circle 6) ----
    def exec_now(kind):
        for p in reversed(exe):
            t = p['terms'][-1]
            if t['type'] == kind and t['start'] <= TODAY < t['end']:
                n = p['name']; return n.get('official_full') or f"{n['first']} {n['last']}"
    leaders = []
    for x in leg:
        for r in x.get('leadership_roles', []):
            if r['title'] in LEADER_TITLES and current(r.get('end')):
                leaders.append({'name': x['name'].get('official_full'), 'role': r['title']})
    leaders.sort(key=lambda r: LEADER_TITLES.index(r['role']))
    national = {
        'president': exec_now('prez'), 'vice_president': exec_now('viceprez'),
        'congressional_leaders': leaders,
        'supreme_court': static['supreme_court'],
        'supreme_court_verified': static['supreme_court_verified'],
    }

    # ---- Congress by state ----
    fed = {s: {'senators': [], 'representatives': []} for s in STATES}
    for x in leg:
        t = x['terms'][-1]; st = t['state']
        if st not in fed: continue
        name = x['name'].get('official_full') or f"{x['name']['first']} {x['name']['last']}"
        if t['type'] == 'sen':
            fed[st]['senators'].append({'name': name, 'role': 'U.S. Senator', 'url': t.get('url')})
        else:
            d = t.get('district', 0)
            role = 'Delegate to Congress' if st == 'DC' else ('U.S. Representative, At-Large' if d == 0 else f'U.S. Representative, {ordinal(d)} District')
            fed[st]['representatives'].append({'name': name, 'role': role, 'district': str(d), 'url': t.get('url')})
    for st in fed:
        fed[st]['representatives'].sort(key=lambda r: int(r['district']))

    index = {'updated': TODAY, 'national': national, 'states': {}}
    for st, name in STATES.items():
        low = st.lower()
        # executives
        execs = []
        for f in glob.glob(os.path.join(PEOPLE, 'data', low, 'executive', '*.yml')):
            p = yaml.safe_load(open(f))
            for r in p.get('roles', []):
                if current(r.get('end_date')) and str(r.get('start_date') or '0000') <= TODAY:
                    role = r['type'].replace('_', ' ').strip().lower()
                    role = {'lt governor': 'lieutenant governor', 'lt. governor': 'lieutenant governor'}.get(role, role)
                    if st == 'DC' and role == 'governor': role = 'mayor'
                    execs.append({'name': p['name'], 'role': ' '.join(w if w in ('of', 'and') else w.capitalize() for w in role.split())})
        execs.sort(key=lambda e: (EXEC_ORDER.index(e['role'].lower()) if e['role'].lower() in EXEC_ORDER else 99, e['role']))
        # legislators
        upper, lower = [], []
        try:
            rows = csv.DictReader(io.StringIO(get(f'https://data.openstates.org/people/current/{low}.csv').decode('utf-8-sig')))
            for r in rows:
                item = {'name': r['name'], 'district': r['current_district']}
                (upper if r['current_chamber'] == 'upper' else lower).append(item)
        except Exception as e:
            print('WARN legislators', st, e, file=sys.stderr)
        keyf = lambda i: (0, int(i['district'])) if i['district'].isdigit() else (1, i['district'])
        upper.sort(key=keyf); lower.sort(key=keyf)
        chambers = {'upper': 'State Senate',
                    'lower': 'State House' if st not in ('CA', 'NV', 'NY', 'WI') else 'State Assembly'}
        if st == 'DC': chambers['lower'] = 'D.C. Council'
        if st == 'NE': chambers['lower'] = 'Unicameral Legislature'
        if st in ('MD', 'VA', 'WV'): chambers['lower'] = 'House of Delegates'
        data = {'state': st, 'name': name, 'updated': TODAY, 'executives': execs,
                'us_senators': fed[st]['senators'], 'us_representatives': fed[st]['representatives'],
                'state_senate': upper, 'state_house': lower, 'chamber_names': chambers}
        json.dump(data, open(os.path.join(OUT, 'states', f'{st}.json'), 'w'), separators=(',', ':'))
        index['states'][st] = {'name': name, 'governor': next((e['name'] for e in execs if e['role'] in ('Governor', 'Mayor')), None),
                               'counts': {'exec': len(execs), 'senate': len(upper), 'house': len(lower), 'congress': len(fed[st]['senators']) + len(fed[st]['representatives'])}}
        print(st, len(execs), len(upper), len(lower), len(fed[st]['senators']), len(fed[st]['representatives']))
    json.dump(index, open(os.path.join(OUT, 'index.json'), 'w'), separators=(',', ':'))

if __name__ == '__main__':
    main()
