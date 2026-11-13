import importlib.util
import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile

spec=importlib.util.spec_from_file_location('directory',Path(__file__).resolve().parents[1]/'scripts/directory.py')
d=importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(d)

def fixture(**kwargs):
    repo=dict(id=1,full_name='example/project',private=False,visibility='public',description=None,topics=[],language=None,license=None,homepage='javascript:alert(1)')
    repo.update(kwargs)
    return {'starred_at':'2026-11-13T00:00:00Z','repo':repo}

class DirectoryTests(unittest.TestCase):
    def test_private_and_unknown_flag_excluded(self):
        for flag in (True,None,0,'false'):
            self.assertIsNone(d.sanitize(fixture(private=flag,full_name='fixture/secret-sentinel'),{},{}))
        self.assertIsNone(d.sanitize(fixture(visibility='private'),{},{}))

    def test_allowlist_and_honest_defaults(self):
        r=d.sanitize(fixture(secret='never-export'),{},{})
        self.assertEqual(set(r),d.FIELDS)
        self.assertEqual(r['categories'],['Needs Review'])
        self.assertFalse(r['reviewed'])
        self.assertEqual(r['website'],'')
        self.assertIn('No description supplied',d.card(r))
        self.assertNotIn('never-export',str(r))

    def test_escape_untrusted_text(self):
        r=d.sanitize(fixture(description='<script>alert(1)</script>',homepage='https://example.org/?x="'),{},{})
        self.assertNotIn('<script>',d.card(r))
        self.assertIn('&lt;script&gt;',d.card(r))
        self.assertNotIn('<script>',d.md(r['description']))

    def test_safe_urls(self):
        for value in ['javascript:alert(1)','data:text/html,a','//example.org','https://user:pass@example.org','https://example.org/\nhello','https://[broken']:
            self.assertEqual(d.safe_url(value),'')
        self.assertEqual(d.safe_url('https://example.org/'),'https://example.org/')

    def test_classification_and_review_gate(self):
        r=d.sanitize(fixture(description='MCP agent'),{'Jewish GitHub':[1]}, {'1':{'reviewed':True}})
        self.assertIn('MCP',r['categories'])
        self.assertIn('Jewish GitHub',r['categories'])
        self.assertFalse(r['reviewed'])
        r=d.sanitize(fixture(),{}, {'1':{'categories':['Torah Library'],'reviewed':True,'review_note':'2026-11-13: Human evidence and documentation review completed.'}})
        self.assertEqual(r['categories'],['Torah Library'])
        self.assertTrue(r['reviewed'])

    def test_empty_fails_closed(self):
        with self.assertRaises(ValueError): d.collect(lambda url:([],''))

    def test_broken_pagination_fails_closed(self):
        for link in ['<https://evil.invalid/>; rel="next"','<https://api.github.com/user/starred>; rel="next"','<bad>; rel="next"']:
            with self.assertRaises(ValueError): d.collect(lambda url:([fixture()]*100,link))

    def test_public_canonical_links_keep_named_requests(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            if len(calls)==1:
                return [fixture()]*100,'<https://api.github.com/user/6117184/starred?per_page=100&page=2>; rel="next"'
            return [fixture(id=2)],''
        with patch.object(Path,'exists',return_value=False):
            result=d.collect(fetch)
        self.assertEqual(len(result['projects']),2)
        self.assertTrue(all('/users/abeperl/starred?' in url for url in calls))

    def test_full_page_without_link_fails_closed(self):
        with self.assertRaises(ValueError): d.collect(lambda url:([fixture()]*100,''))

    def test_failed_request_does_not_fallback(self):
        def broken(url): raise OSError('upstream unavailable')
        with self.assertRaises(OSError): d.collect(broken)

    def test_dedupe_and_second_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'config').mkdir()
            (root/'config/public-lists.json').write_text('{"lists":{}}')
            (root/'config/overrides.json').write_text('{}')
            with patch.object(d,'ROOT',root):
                result=d.collect(lambda url:([fixture(),fixture(),fixture(private=True,full_name='fixture/secret-sentinel')],''))
                self.assertEqual(len(result['projects']),1)
                self.assertNotIn('secret-sentinel',str(result))
                (root/'data').mkdir()
                (root/'data/catalog.json').write_text('{"projects":[{},{},{}]}')
                with self.assertRaises(ValueError): d.collect(lambda url:([fixture()],''))

    def test_page_has_static_content_and_canonical(self):
        r=d.sanitize(fixture(),{},{})
        text=d.page('Title','Description',[r],'',{'collected_at':'2026-11-13','projects':[r]})
        self.assertIn('rel="canonical"',text)
        self.assertIn('example/project',text)
        self.assertIn('id="search"',text)
        self.assertIn('No description supplied',text)
        self.assertIn('Skip to projects',text)

if __name__=='__main__': unittest.main()
