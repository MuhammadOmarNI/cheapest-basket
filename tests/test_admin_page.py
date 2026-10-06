"""
اختبار صفحة الأدمن في متصفح حقيقي، والباكند مزيّف.

بنعترض كل نداء للـ API ونرد بردود جاهزة — فاللي بنختبره هو الصفحة
نفسها: هل بتقرا الحالة صح، بتغيّر الطريقة، بتتابع التقدم، بتعرض
الجدول، وبتقول إيه لما السيرفر يقع.
"""
from playwright.sync_api import sync_playwright
import json, pathlib, sys

W = pathlib.Path('/tmp/claude-0/-home-claude/08902a29-63c7-5eb8-bfbc-14187226ca0e/scratchpad/adm')

failures, errors = [], []
state = {'mode': 'site', 'tick': 0, 'refresh_started': False}


def check(label, cond, detail=''):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + ('' if cond else f'  {detail}'))
    if not cond:
        failures.append(label)


def json_route(route, body, status=200):
    route.fulfill(status=status, content_type='application/json', body=json.dumps(body))


PRICE_ROWS = [
    {'sku': '2900882', 'name': 'KIRNI PILIC GOGUS FILLET', 'price': 322.0, 'currency': 'TRY',
     'category': 'tavuk', 'url': 'https://www.kibrissanalmarket.com/urunler/x/',
     'fetched_at': '2026-09-26T21:00:00Z', 'source': 'kibrissanalmarket.com'},
    {'sku': '2009530000144', 'name': 'EKMEK', 'price': 28.0, 'currency': 'TRY',
     'category': 'ekmek-pide-yufka', 'url': None,
     'fetched_at': '2026-09-26T21:00:00Z', 'source': 'kibrissanalmarket.com'},
]


def api(route):
    url = route.request.url
    method = route.request.method

    if '/units' in url:
        return json_route(route, {'units': [
            {'value': 'g', 'label': 'g'}, {'value': 'kg', 'label': 'kg'},
            {'value': 'ml', 'label': 'ml'}, {'value': 'l', 'label': 'L'},
            {'value': 'piece', 'label': 'piece'}]})

    if '/price' in url and method == 'POST':
        body = json.loads(route.request.post_data)
        state['asked'] = body
        return json_route(route, {
            'ingredient': body['ingredient'], 'low': 150.0, 'high': 179.9,
            'basis': str(body['qty']).rstrip('0').rstrip('.') + ' ' + body['unit'].upper(),
            'ignored': 1, 'provisional': False,
            'observations': [
                {'price': 75.0, 'shop': 'KOOP 1L SUT', 'source': 'https://x/1',
                 'size': '1 L', 'unit_price': 75.0, 'total': 150.0},
                {'price': 17.99, 'shop': 'SUT 200ML', 'source': 'https://x/2',
                 'size': '0.2 L', 'unit_price': 89.95, 'total': 179.9},
                {'price': 478.99, 'shop': 'ALASKA 1KG SUT', 'source': '',
                 'size': '1 KG', 'unit_price': 478.99, 'total': None},
            ]})

    if '/config' in url:
        return json_route(route, {'gemini_ready': True, 'supabase_ready': True})

    if '/admin/settings' in url:
        if method == 'PUT':
            state['mode'] = json.loads(route.request.post_data)['mode']
        return json_route(route, {'id': 1, 'price_mode': state['mode']})

    if '/admin/refresh/status' in url:
        if not state['refresh_started']:
            return json_route(route, {'running': False, 'stage': 'idle', 'done': 0,
                                      'total': 0, 'message': 'لسه ما اتحدّثش'})
        state['tick'] += 1
        if state['tick'] <= 2:
            return json_route(route, {'running': True, 'stage': 'crawling',
                                      'done': state['tick'] * 20, 'total': 71,
                                      'products': 300,
                                      'message': f"{state['tick']*20}/71 — 300 منتج"})
        return json_route(route, {'running': False, 'stage': 'done', 'done': 71,
                                  'total': 71, 'saved': 1487,
                                  'message': 'خلص — 1487 منتج محفوظ'})

    if '/admin/refresh' in url and method == 'POST':
        state['refresh_started'] = True
        return json_route(route, {'started': True})

    if '/admin/prices' in url:
        q = ''
        if 'q=' in url:
            q = url.split('q=')[-1].split('&')[0]
        rows = PRICE_ROWS if not q or 'tavuk' in q.lower() else []
        return json_route(route, {'summary': {'count': 1487,
                                              'last_updated': '2026-09-26T21:00:00Z'},
                                  'rows': rows})

    return json_route(route, {'detail': 'unexpected ' + url}, status=404)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    page = b.new_page(viewport={'width': 1000, 'height': 1200})
    page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
    page.on('console', lambda m: errors.append(f'{m.type}: {m.text}') if m.type == 'error' else None)
    page.route('**/127.0.0.1:8010/**', api)

    page.goto((W / 'admin.html').as_uri())
    page.wait_for_timeout(900)

    # ================================================================ load ==
    print('== أول تحميل ==')
    check('اتصل بالسيرفر', page.locator('#api-state').inner_text().strip() == 'متصل',
          page.locator('#api-state').inner_text())
    check('قرا الطريقة الحالية', page.locator('#modes input[value="site"]').is_checked())
    check('كتب اسم الطريقة', 'زحف' in page.locator('#mode-state').inner_text())
    check('عرض عدد المنتجات', '1487' in page.locator('#db-summary').inner_text(),
          page.locator('#db-summary').inner_text())
    check('الجدول فيه صفين', page.locator('#prices tbody tr').count() == 2)
    check('السعر متنسّق بالليرة', '₺' in page.locator('#prices tbody tr').first.inner_text())
    check('اسم المنتج لينك', page.locator('#prices tbody tr').first.locator('a').count() == 1)
    check('مفيش nav في صفحة الأدمن', page.locator('.nav').count() == 0)
    check('الشريط البسيط موجود', page.locator('.topbar-bare').count() == 1)
    check('وفيه رجوع للتطبيق', 'Back to the app' in page.locator('.topbar-bare').inner_text(),
          page.locator('.topbar-bare').inner_text())
    check('شريط التقدم مخفي', page.locator('#progress').is_hidden())

    # ============================================================== try price ==
    print('\n== جرّب سعر ==')
    opts = [o.inner_text().strip() for o in page.locator('#try-unit option').all()]
    print('   الوحدات:', opts)
    check('الـ select اتملى من /units', len(opts) == 5, opts)
    check('المبدئي لتر', page.locator('#try-unit').input_value() == 'l')

    page.fill('#try-ingredient', 'milk')
    page.fill('#try-qty', '2')
    page.select_option('#try-unit', 'l')
    page.click('#try-btn')
    page.wait_for_timeout(600)

    check('بعت الكمية والوحدة للسيرفر',
          state['asked']['qty'] == 2 and state['asked']['unit'] == 'l', state.get('asked'))
    body = page.locator('#try-result').inner_text()
    print('   النتيجة:', body.split('\n')[0:3])
    check('عرض المدى', '150' in body and '179' in body, body[:80])
    check('وعرض الأساس', '2 L' in body, body[:80])
    check('ونبّه على المستبعد', 'وحدة مختلفة' in body, body[:120])
    check('الصف المستبعد باهت', page.locator('#try-result tr.dim').count() == 1)
    check('عمود سعر الوحدة موجود', 'سعر الوحدة' in body)

    page.select_option('#try-unit', 'kg')
    page.fill('#try-qty', '0.5')
    page.click('#try-btn')
    page.wait_for_timeout(600)
    check('تغيير الوحدة بيوصل', state['asked']['unit'] == 'kg' and state['asked']['qty'] == 0.5,
          state.get('asked'))

    # ============================================================ mode swap ==
    print('\n== تغيير الطريقة ==')
    page.click('#modes input[value="ai"]')
    page.wait_for_timeout(500)
    check('اتحفظت على السيرفر', state['mode'] == 'ai', state['mode'])
    check('الوصف اتغيّر', 'مؤرّض' in page.locator('#mode-state').inner_text(),
          page.locator('#mode-state').inner_text())
    bg = page.evaluate("getComputedStyle(document.querySelector('#modes label:nth-child(2)')).backgroundColor")
    check('الكارتونة المختارة اتلوّنت', bg != 'rgb(255, 255, 255)', bg)

    page.click('#modes input[value="site"]')
    page.wait_for_timeout(400)
    check('رجعت للزحف', state['mode'] == 'site')

    # ============================================================== refresh ==
    print('\n== التحديث ==')
    page.click('#refresh-btn')
    page.wait_for_timeout(700)
    check('بدأ التحديث', state['refresh_started'])
    check('الزر اتقفل', page.locator('#refresh-btn').is_disabled())
    check('الشريط ظهر', not page.locator('#progress').is_hidden())

    page.wait_for_timeout(3400)      # الـ polling كل 3 ثواني
    pct = page.locator('#progress-value').inner_text()
    print('   النسبة وقت الشغل:', pct)
    check('النسبة اتحسبت', pct not in ('', '0%'), pct)

    # نستنى لحد ما يخلص
    page.wait_for_function("() => !document.getElementById('refresh-btn').disabled",
                           timeout=20000)
    check('الزر رجع يشتغل', not page.locator('#refresh-btn').is_disabled())
    check('الشريط اختفى', page.locator('#progress').is_hidden())
    check('قال إنه خلص', '1487' in page.locator('#refresh-msg').inner_text(),
          page.locator('#refresh-msg').inner_text())

    # =============================================================== search ==
    print('\n== البحث ==')
    page.fill('#search', 'tavuk')
    page.click('#search-btn')
    page.wait_for_timeout(600)
    check('لقى نتيجة', page.locator('#prices tbody tr').count() == 2)

    page.fill('#search', 'zzzz')
    page.press('#search', 'Enter')
    page.wait_for_timeout(600)
    body = page.locator('#prices tbody').inner_text()
    check('بحث فاشل بيقول مفيش نتيجة', 'مفيش نتيجة' in body, body[:80])

    # ========================================================= server down ==
    print('\n== لما السيرفر يقع ==')
    page.unroute('**/127.0.0.1:8010/**')
    page.route('**/127.0.0.1:8010/**', lambda r: r.abort('connectionrefused'))
    page.reload()
    page.wait_for_timeout(1200)
    msg = page.locator('#api-state').inner_text()
    print('   بيقول:', msg)
    check('بيشرح المشكلة مش بيسكت', 'مش شغّال' in msg, msg)
    check('والجدول كمان', 'مش شغّال' in page.locator('#prices tbody').inner_text())

    # ================================================================ phone ==
    print('\n== عرض الموبايل ==')
    page.unroute('**/127.0.0.1:8010/**')
    page.route('**/127.0.0.1:8010/**', api)
    page.reload()
    page.wait_for_timeout(900)
    page.set_viewport_size({'width': 390, 'height': 900})
    page.wait_for_timeout(400)
    over = page.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
    check('مفيش سكرول أفقي', over <= 0, f'بيزيد {over}px')
    cols = page.evaluate("getComputedStyle(document.getElementById('modes')).gridTemplateColumns")
    check('الخيارات بقت عمود واحد', len(cols.split()) == 1, cols)
    page.screenshot(path=str(W / '../admin-mobile.png'), full_page=True)

    page.set_viewport_size({'width': 1000, 'height': 1200})
    page.fill('#try-ingredient', 'milk')
    page.fill('#try-qty', '2')
    page.select_option('#try-unit', 'l')
    page.click('#try-btn')
    page.wait_for_timeout(700)
    rowH = page.evaluate("getComputedStyle(document.querySelector('.try-row')).gridTemplateColumns")
    check('صف التجربة 4 أعمدة', len(rowH.split()) == 4, rowH)
    page.screenshot(path=str(W / '../admin-desktop.png'), full_page=True)

    b.close()

print('\n== console ==')
# اختبار "السيرفر واقع" بيولّد الغلط ده عن قصد — المتصفح بيسجّله
# سواء تعاملنا معاه ولا لأ، وإحنا متعاملين معاه.
expected = [e for e in errors if 'ERR_CONNECTION_REFUSED' in e]
errors = [e for e in errors if 'ERR_CONNECTION_REFUSED' not in e]
if expected:
    print(f'   ({len(expected)} غلط متوقّع من اختبار انقطاع السيرفر، متجاهَل)')
if errors:
    for e in errors:
        print('  ', e)
else:
    print('   ok   مفيش أخطاء')

print('\n' + ('ALL PASSED' if not failures and not errors else f'PROBLEMS: {failures} {errors}'))
sys.exit(1 if failures or errors else 0)
