"""
اختبار الموقع وهو متقدّم من سيرفر حقيقي (زي Vercel) مش من file://.

الفرق المهم: api.js المفروض يلاقي الـ API على نفس الدومين تحت /api،
من غير أي إعداد. ولو مش موجود، يرجع للسيرفر المحلي، ولو مفيش ده
ولا ده، التطبيق يفضل شغّال بأسعار يدوية.
"""
from playwright.sync_api import sync_playwright
import http.server, json, pathlib, shutil, socketserver, threading, sys

SRC = pathlib.Path('/mnt/user-data/outputs/deploy')
W = pathlib.Path('/tmp/claude-0/-home-claude/08902a29-63c7-5eb8-bfbc-14187226ca0e/scratchpad/hosted')
SHOTS = W.parent / 'shots4'

failures, console = [], []
hits = []


def check(label, cond, detail=''):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + ('' if cond else f'  {detail}'))
    if not cond:
        failures.append(label)


if W.exists():
    shutil.rmtree(W)
W.mkdir(parents=True)
SHOTS.mkdir(exist_ok=True)
for item in ['index.html', 'meals.html', 'compare.html', 'game.html',
             'settings.html', 'login.html', 'admin.html']:
    shutil.copy(SRC / item, W / item)
shutil.copytree(SRC / 'js', W / 'js')
shutil.copytree(SRC / 'css', W / 'css')


class Handler(http.server.SimpleHTTPRequestHandler):
    """سيرفر ثابت + تقليد للـ rewrite بتاع Vercel: /api/* → الدالة."""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(W), **kw)

    def log_message(self, *a):
        pass

    def _api(self, body=None):
        hits.append((self.command, self.path))
        if self.path.startswith('/api/config'):
            return self._json({'gemini_ready': True, 'supabase_ready': True,
                               'admin_protected': True, 'can_refresh': False,
                               'price_source': 'Kıbrıs Sanal Market'})
        if self.path.startswith('/api/units'):
            return self._json({'units': [{'value': 'g', 'label': 'g'},
                                         {'value': 'kg', 'label': 'kg'},
                                         {'value': 'ml', 'label': 'ml'},
                                         {'value': 'l', 'label': 'L'},
                                         {'value': 'piece', 'label': 'piece'}]})
        if self.path.startswith('/api/price'):
            return self._json({'ingredient': 'milk', 'low': 150.0, 'high': 179.9,
                               'basis': '2 L', 'ignored': 1, 'provisional': False,
                               'observations': [
                                   {'price': 75.0, 'shop': 'KOOP 1L SUT',
                                    'source': 'https://x/1', 'size': '1 L',
                                    'unit_price': 75.0, 'total': 150.0}]})
        if self.path.startswith('/api/admin/settings'):
            return self._json({'id': 1, 'price_mode': 'site'})
        if self.path.startswith('/api/admin/prices'):
            return self._json({'summary': {'count': 1099, 'last_updated': None}, 'rows': []})
        return self._json({'detail': 'not found'}, 404)

    def _json(self, payload, status=200):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.startswith('/api/'):
            return self._api()
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/'):
            length = int(self.headers.get('Content-Length') or 0)
            self.rfile.read(length)
            return self._api()
        self.send_error(405)

    def do_PUT(self):
        return self.do_POST()


socketserver.TCPServer.allow_reuse_address = True
server = socketserver.TCPServer(('127.0.0.1', 8099), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
HOST = 'http://127.0.0.1:8099'

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    page = b.new_page(viewport={'width': 1100, 'height': 900})
    page.on('pageerror', lambda e: console.append(f'PAGEERROR: {e}'))
    page.on('console', lambda m: console.append(f'{m.type}: {m.text}') if m.type == 'error' else None)
    page.route('**://**supabase.co/**', lambda r: r.abort())
    # السيرفر المحلي مش شغّال — لازم يلاقي نفس الدومين لوحده
    page.route('**/127.0.0.1:8010/**', lambda r: r.abort('connectionrefused'))

    # ================================================= اكتشاف الـ API ==
    print('== بيلاقي الـ API على نفس الدومين ==')
    page.goto(HOST + '/compare.html')
    page.wait_for_timeout(1500)

    paths = [h[1] for h in hits]
    print('   طلبات الـ API:', paths[:4])
    check('سأل /api/config على نفس الدومين',
          any(x.startswith('/api/config') for x in paths), paths)
    check('ما جربش 8010 الأول',
          paths and paths[0].startswith('/api/'), paths[:2])

    # ======================================================= الأساسيات ==
    print('\n== الصفحات ==')
    for name in ['index.html', 'meals.html', 'compare.html', 'game.html', 'settings.html']:
        page.goto(HOST + '/' + name)
        page.wait_for_timeout(500)
        check(f'{name}: اتحمّلت', page.locator('.nav').count() == 1)
        check(f'{name}: شريط اللغة', page.locator('.langbar').count() == 1)

    # ================================================ جلب سعر حقيقي ==
    print('\n== جلب سعر ==')
    page.goto(HOST + '/meals.html')
    page.wait_for_timeout(700)
    page.locator('main.page button', has_text='New meal').first.click()
    page.wait_for_timeout(300)
    page.fill('#new-meal-name', 'Test')
    page.press('#new-meal-name', 'Enter')
    page.wait_for_timeout(600)
    page.fill('#ing-name', 'milk')
    page.fill('#ing-qty', '2')
    page.select_option('#ing-unit', 'l')
    page.press('#ing-name', 'Enter')
    page.wait_for_timeout(500)

    page.goto(HOST + '/compare.html')
    page.wait_for_timeout(1500)
    btn = page.locator('#ask-ai-btn')
    check('الزرار ظاهر', not btn.is_hidden())
    btn.click()
    page.wait_for_timeout(2000)
    body = page.locator('#view').inner_text()
    check('السعر اتحط من /api/price', '150' in body, body[:120])
    page.screenshot(path=str(SHOTS / 'hosted-compare.png'), full_page=True)

    # ======================================= الأدمن: مفيش زرار تحديث ==
    print('\n== الأدمن على استضافة ==')
    page.goto(HOST + '/admin.html')
    page.wait_for_timeout(1600)
    check('زرار التحديث اتخفى', page.locator('#refresh-btn').is_hidden())
    msg = page.locator('#refresh-msg').inner_text()
    print('   بيقول:', msg[:90])
    check('وقال ليه', 'tools/refresh.py' in msg, msg)
    check('وباقي الصفحة شغّالة', page.locator('#modes input:checked').count() == 1)
    page.screenshot(path=str(SHOTS / 'hosted-admin.png'), full_page=True)

    # ============================== من غير API خالص: التطبيق لسه شغّال ==
    print('\n== من غير أي سيرفر ==')
    page.unroute('**/127.0.0.1:8010/**')
    page.route('**/api/**', lambda r: r.abort('connectionrefused'))
    page.route('**/127.0.0.1:8010/**', lambda r: r.abort('connectionrefused'))
    page.goto(HOST + '/compare.html')
    page.wait_for_timeout(2000)
    check('زرار الجلب اتخفى', page.locator('#ask-ai-btn').is_hidden())
    body = page.locator('#view').inner_text()
    check('وقال لليوزر يعمل إيه', 'uvicorn' in body, body[-150:])
    check('والأسعار المحفوظة باقية', '150' in body)

    b.close()

server.shutdown()

print('\n== console ==')
real = [c for c in dict.fromkeys(console)
        if 'ERR_CONNECTION_REFUSED' not in c and 'Failed to load resource' not in c]
print('  ', '\n   '.join(real) if real else 'ok   مفيش أخطاء')

print('\n' + ('ALL PASSED' if not failures and not real else f'PROBLEMS: {failures} {real}'))
sys.exit(1 if failures or real else 0)
