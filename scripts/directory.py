"""Public-only ingestion and dependency-free static publishing. Run in Actions only."""
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys
import urllib.request
from urllib.parse import urlsplit

BASE = 'https://abeperl.github.io/awesome-stars/'
ROOT = Path(__file__).resolve().parents[1]
RULES = {
    'AI & Agents': r'\b(llm|agent|artificial intelligence|chatbot|machine learning|gpt|ollama)\b',
    'MCP': r'\b(mcp|model context protocol)\b',
    'Self-hosted': r'\b(self.hosted|selfhosting|homelab)\b',
    'Developer Tools': r'\b(developer tools|devtools|cli|code editor|debugger|sdk)\b',
    'Web & Apps': r'\b(web app|webapp|react|nextjs|flask|django|android|ios)\b',
    'Data & Search': r'\b(database|search engine|sqlite|postgresql|data analysis|scraping)\b',
    'Learning & Reference': r'\b(tutorial|learning resources|awesome.list|cheatsheet|curriculum)\b',
    'Security & Privacy': r'\b(cybersecurity|encryption|privacy|password manager)\b',
    'Media & Creative': r'\b(video|audio|image generation|music|animation)\b',
    'Jewish GitHub': r'\b(jewish|judaism|hebrew|yiddish|torah|talmud|sefaria)\b',
    'Torah Library': r'\b(torah library|sefaria|talmud|tanakh)\b',
}
FIELDS = {'id','name','url','description','topics','language','license','stars','updated_at','starred_at','archived','fork','website','categories','category_source','reviewed'}

def safe_url(value):
    if not isinstance(value, str) or any(c.isspace() or ord(c)<32 for c in value):
        return ''
    try:
        p = urlsplit(value)
        return value if p.scheme in ('http','https') and p.hostname and not p.username and not p.password else ''
    except ValueError:
        return ''

def clean(value, limit=1000):
    return ''.join(c for c in str(value or '') if ord(c)>=32)[:limit]

def sanitize(item, lists, overrides):
    r = item.get('repo', {})
    if r.get('private') is not False or r.get('visibility', 'public') != 'public':
        return None
    name = r.get('full_name', '')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', name) or type(r.get('id')) is not int:
        raise ValueError('Invalid public repository identity')
    topics = [clean(t,80) for t in r.get('topics',[]) if isinstance(t,str)]
    desc = clean(r.get('description'))
    rid = r['id']
    manual = overrides.get(str(rid), {})
    explicit = [k for k,v in lists.items() if rid in v]
    inferred = [k for k,pattern in RULES.items() if re.search(pattern, ' '.join([name,desc,*topics]), re.I)]
    categories = manual.get('categories') or sorted(set(explicit+inferred)) or ['Needs Review']
    if any(c not in [*RULES,'Needs Review'] for c in categories):
        raise ValueError('Unknown category')
    return dict(id=rid,name=name,url='https://github.com/'+name,description=desc,topics=topics,
                language=clean(r.get('language'),80) or 'Unknown',license=clean((r.get('license') or {}).get('spdx_id'),80) or 'Unspecified',
                stars=max(0,int(r.get('stargazers_count',0))),updated_at=clean(r.get('updated_at'),40),starred_at=clean(item.get('starred_at'),40),
                archived=r.get('archived') is True,fork=r.get('fork') is True,website=safe_url(r.get('homepage')),
                categories=categories,category_source='manual override' if manual.get('categories') else 'public list + metadata' if explicit else 'metadata rules' if inferred else 'unclassified',
                reviewed=manual.get('reviewed') is True and bool(manual.get('review_note')))

def public_page(url):
    # Never accept another endpoint, host or redirect, even from a Link header.
    if not re.fullmatch(r'https://api.github.com/users/abeperl/starred\?per_page=100&page=\d+',url):
        raise ValueError('Disallowed endpoint')
    headers={'Accept':'application/vnd.github.star+json','User-Agent':'awesome-stars-public-directory'}
    if os.environ.get('GITHUB_TOKEN'):
        headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):
            raise ValueError('Redirect refused')
    with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url,headers=headers),timeout=45) as response:
        return json.load(response), response.headers.get('Link','')

def collect(fetch=public_page):
    lists=json.loads((ROOT/'config/public-lists.json').read_text())['lists']
    overrides=json.loads((ROOT/'config/overrides.json').read_text())
    result={}
    for page in range(1,101):
        data,link=fetch(f'https://api.github.com/users/abeperl/starred?per_page=100&page={page}')
        if not isinstance(data,list) or len(data)>100:
            raise ValueError('Invalid public response')
        for item in data:
            row=sanitize(item,lists,overrides)
            if row: result[row['id']]=row
        if not link: break
        next_links=re.findall(r'<([^>]+)>;\s*rel="next"',link)
        if not next_links: 
            if 'rel="next"' in link: raise ValueError('Malformed pagination')
            break
        expected=f'https://api.github.com/users/abeperl/starred?per_page=100&page={page+1}'
        if next_links != [expected] or len(data)!=100:
            raise ValueError('Incomplete pagination')
    else: raise ValueError('Pagination bound exceeded')
    if not result: raise ValueError('Empty snapshot refused')
    prior=ROOT/'data/catalog.json'
    if prior.exists() and len(result)<len(json.loads(prior.read_text())['projects'])*0.8:
        raise ValueError('Large count decrease requires maintainer review')
    return {'collected_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),'projects':sorted(result.values(),key=lambda r:r['name'].lower())}

def esc(s): return html.escape(str(s),quote=True)
def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')
def card(r):
    attrs={'name':r['name'].lower(),'search':' '.join([r['name'],r['description'],*r['topics'],*r['categories']]).lower(),'language':r['language'],'license':r['license'],'status':'Archived' if r['archived'] else 'Active','stars':r['stars'],'updated':r['updated_at'],'starred':r['starred_at'],'reviewed':str(r['reviewed']).lower()}
    data=' '.join(f'data-{k}="{esc(v)}"' for k,v in attrs.items())
    badges=['Collected']+(['Reviewed'] if r['reviewed'] else [])+(['Archived'] if r['archived'] else [])+(['Fork'] if r['fork'] else [])
    return f'<article class="card" {data}><div class="badges">'+''.join(f'<span>{b}</span>' for b in badges)+f'</div><h2><a href="{esc(r["url"])}">{esc(r["name"])}</a></h2><p>{esc(r["description"] or "No description supplied")}</p><p class="meta">{esc(r["language"])} · {esc(r["license"])} · ★ {r["stars"]:,}</p><p class="tags">'+ ' '.join(f'<a href="{BASE}categories/{slug(c)}/">{esc(c)}</a>' for c in r['categories'])+f'</p><p class="meta">Classification: {esc(r["category_source"])} · Updated {esc(r["updated_at"][:10])}</p>'+ (f'<a href="{esc(r["website"])}" rel="noopener noreferrer">Project website ↗</a>' if r['website'] else '')+'</article>'

def page(title,description,rows,path,snapshot,extra=''):
    def select(key,label,values):
        return f'<label>{label}<select id="{key}"><option value="">All</option>'+''.join(f'<option>{esc(v)}</option>' for v in sorted(set(values)))+'</select></label>'
    controls='<section class="controls" aria-label="Search and filter"><label class="search">Search projects<input id="search" type="search" placeholder="Name, topic, description…"></label>'
    controls+=select('language','Language',[r['language'] for r in rows])+select('license','License',[r['license'] for r in rows])+select('status','Status',['Active','Archived'])
    controls+='<label>Sort<select id="sort"><option value="name">Name A–Z</option><option value="stars">Popularity (stars)</option><option value="updated">Recently updated</option><option value="starred">Recently starred</option></select></label></section>'
    nav=''.join(f'<a href="{BASE}categories/{slug(c)}/">{esc(c)}</a>' for c in sorted({c for r in snapshot['projects'] for c in r['categories']}))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)} · Awesome Stars</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{BASE+path}"><meta property="og:title" content="{esc(title)} · Awesome Stars"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{BASE+path}"><meta property="og:type" content="website"><meta name="color-scheme" content="light dark"><link rel="stylesheet" href="{BASE}style.css"><script defer src="{BASE}search.js"></script></head><body><a class="skip" href="#main">Skip to projects</a><header><a class="brand" href="{BASE}">✳ Awesome Stars</a><nav aria-label="Main"><a href="{BASE}reviewed/">Reviewed Awesome list</a><a href="https://github.com/abeperl/awesome-stars">Source & contribute ↗</a></nav></header><main id="main"><section class="hero"><p class="eyebrow">OPEN SOURCE DISCOVERY / PUBLIC GITHUB STARS</p><h1>{esc(title)}</h1><p class="intro">{esc(description)}</p><p>Collected, not endorsed. Metadata-based categories are provisional; public-list membership is not editorial review.</p><p class="meta">Snapshot {esc(snapshot['collected_at'][:10])} · {len(snapshot['projects']):,} collected projects · {sum(r['reviewed'] for r in snapshot['projects'])} reviewed</p>{extra}</section><nav class="categories" aria-label="Categories">{nav}</nav>{controls}<p id="count" role="status" aria-live="polite">{len(rows):,} projects</p><section id="projects" class="grid" aria-label="Projects">{''.join(card(r) for r in rows)}</section><p id="empty" hidden>No projects match these filters. Try clearing the search.</p><noscript>All projects are visible without JavaScript. Use your browser’s Find command to search.</noscript></main><footer><p>No tracking, paid placement, or automated endorsements. Verify security, maintenance and licensing before use. GitHub stars are not a quality guarantee.</p><p>Code MIT. Project metadata and trademarks belong to their respective owners; inclusion grants no license. <a href="https://github.com/abeperl/awesome-stars/blob/main/CONTRIBUTING.md">Editorial policy & corrections</a></p></footer></body></html>'''

def md(s):
    return html.escape(str(s)).replace('\\','\\\\').replace('[','\\[').replace(']','\\]').replace('*','\\*').replace('_','\\_').replace('|','\\|').replace('`','\\`')

def build(snapshot,dest):
    rows=snapshot['projects']
    if not rows or any(set(r)!=FIELDS for r in rows): raise ValueError('Invalid catalog schema')
    dest.mkdir(parents=True,exist_ok=True)
    categories=sorted({c for r in rows for c in r['categories']})
    pages=[('', 'Explore public GitHub projects', 'A searchable collection of public GitHub stars: AI agents, MCP, self-hosted tools, Jewish software, Torah libraries and more.',rows),('reviewed/','Reviewed Awesome list','A smaller editorially reviewed list, separate from the complete collected directory.',[r for r in rows if r['reviewed']])]
    pages += [(f'categories/{slug(c)}/',c,f'Explore {c} projects from a public GitHub stars collection. Browse descriptions, languages, licenses and repository links.',[r for r in rows if c in r['categories']]) for c in categories]
    for path,title,desc,subset in pages:
        target=dest/path; target.mkdir(parents=True,exist_ok=True)
        extra='<p>No projects have completed editorial review yet. Nothing is recommended by default.</p>' if path=='reviewed/' and not subset else ''
        (target/'index.html').write_text(page(title,desc,subset,path,snapshot,extra))
    for asset in ['style.css','search.js']: shutil.copyfile(ROOT/'assets'/asset,dest/asset)
    (dest/'.nojekyll').write_text('')
    (dest/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n')
    (dest/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{BASE}{p[0]}</loc></url>' for p in pages)+'</urlset>')
    readme=f'''# Awesome Stars

[Search the directory]({BASE}) · [Reviewed Awesome list]({BASE}reviewed/) · [Contribute](CONTRIBUTING.md)

A public GitHub stars collection, **not endorsements**. {len(rows):,} collected projects; {sum(r['reviewed'] for r in rows)} editorially reviewed. Snapshot: {snapshot['collected_at'][:10]}.

## Reviewed Awesome list

No projects have completed editorial review yet. Collection, public GitHub List membership, and automatic classification do not qualify as review. See [editorial criteria](CONTRIBUTING.md).

## Browse the collection

Projects can appear in multiple categories. Public List mappings (Jewish GitHub and Torah Library) precede deterministic topic/description rules; ambiguous projects remain Needs Review. Missing descriptions are reported honestly. List membership snapshot is dated in config/public-lists.json; metadata refreshes daily. No paid recommendations or tracking.

'''
    for c in categories:
        subset=[r for r in rows if c in r['categories']]
        readme+=f'- [{c} ({len(subset)})]({BASE}categories/{slug(c)}/)\n'
    for c in categories:
        readme+=f'\n## {c}\n\n'
        for r in rows:
            if c in r['categories']:
                badges=(' · Archived' if r['archived'] else '')+(' · Fork' if r['fork'] else '')
                readme+=f'- [{md(r["name"])}]({r["url"]}) — {md(r["description"] or "No description supplied")} ({md(r["language"])}; {md(r["license"])}{badges})\n'
    readme+='\n## Attribution & maintenance\n\nMetadata from the public GitHub API. Project authors retain all rights and trademarks. Inclusion grants no license and implies no affiliation, endorsement, security audit, or maintenance guarantee. Site code: [MIT](LICENSE). See [maintenance and privacy](MAINTENANCE.md).\n'
    (ROOT/'README.md').write_text(readme)
    print(f'Validated publication: {len(rows)} projects; {len(categories)} categories; {len(pages)} HTML pages; {sum(r["reviewed"] for r in rows)} reviewed')

if __name__=='__main__':
    if os.environ.get('GITHUB_ACTIONS')!='true': raise SystemExit('Generation is restricted to GitHub Actions')
    snapshot=collect()
    # Only the explicitly allowlisted schema is ever written; raw responses stay in memory.
    (ROOT/'data').mkdir(exist_ok=True)
    (ROOT/'data/catalog.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n')
    build(snapshot,ROOT/'site')
