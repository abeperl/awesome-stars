"""Chromium smoke checks, executed only on hosted Actions runners."""
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.path=self.path.replace('/awesome-stars/','/site/',1)
        return super().do_GET()
    def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',8765),functools.partial(Handler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
projects=json.loads((root/'data/catalog.json').read_text())['projects']
count=len(projects)
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    # Test production absolute URLs against the runner's local static server.
    page.route('https://abeperl.github.io/awesome-stars/**',lambda route:route.fulfill(response=route.fetch(url=route.request.url.replace('https://abeperl.github.io','http://127.0.0.1:8765'))))
    page.goto('http://127.0.0.1:8765/awesome-stars/')
    page.wait_for_selector('article')
    assert page.locator('article').count()==count
    page.locator('#search').fill('nonexistent-project-sentinel-xyz')
    page.wait_for_timeout(350)
    assert page.locator('article:visible').count()==0
    assert page.locator('#empty').is_visible()
    page.locator('#search').fill('')
    page.wait_for_timeout(350)
    assert page.locator('article:visible').count()==count
    page.select_option('#status','Archived')
    page.wait_for_timeout(350)
    assert page.locator('article:visible').count()==sum(r['archived'] for r in projects)
    for c in page.locator('article:visible').all(): assert c.get_attribute('data-status')=='Archived'
    page.select_option('#status','')
    page.select_option('#sort','stars')
    page.wait_for_timeout(350)
    numbers=page.locator('article').evaluate_all('(cards)=>cards.map(c=>Number(c.dataset.stars))')
    assert numbers==sorted(numbers,reverse=True)
    page.screenshot(path=str(root/'site/desktop-preview.png'))
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(root/'site/mobile-preview.png'))
    page.goto('http://127.0.0.1:8765/awesome-stars/reviewed/')
    assert page.locator('article').count()==0
    assert 'No projects have completed' in page.inner_text('main')
    page.goto('http://127.0.0.1:8765/awesome-stars/categories/torah-library/')
    assert page.locator('article').count()>0
    assert not errors,errors
    browser.close()
    browser=p.chromium.launch()
    context=browser.new_context(java_script_enabled=False)
    page=context.new_page()
    page.goto('http://127.0.0.1:8765/awesome-stars/')
    assert page.locator('article').count()==count
    browser.close()
server.shutdown()
print(f'Chromium verified: {count} crawlable cards, search, status filter, popularity sort, mobile overflow, categories, empty reviewed, no-JS content; no JS errors')
