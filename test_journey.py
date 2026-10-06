"""
المشوار كامل: يوزر جديد → وجبة → وحدات → جلب أسعار → مقارنة → داشبورد → لعبة.

الباكند مزيّف، فاللي بنختبره هو التطبيق نفسه: هل بيطلب الصح، وبيحط
الأسعار في المكان الصح، وبيقول الحقيقة لليوزر.
"""
from playwright.sync_api import sync_playwright
import json, pathlib, shutil, sys, re

SRC = pathlib.Path('/mnt/user-data/outputs/basket')
W = pathlib.Path('/tmp/claude-0/-home-claude/08902a29-63c7-5eb8-bfbc-14187226ca0e/scratchpad/journey')
SHOTS = W.parent / 'shots2'

failures, console = [], []
asked = []


def check(label, cond, detail=''):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + ('' if cond else f'  {detail}'))
    if not cond:
        failures.append(label)


if W.exists():
    shutil.rmtree(W)
shutil.copytree(SRC, W)
SHOTS.mkdir(exist_ok=True)

PRICES = {
    'chicken breast': {'low': 322.0, 'high': 322.0, 'basis': '1 kg', 'ignored': 0,
                       'observations': [{'price': 322.0, 'shop': 'KIRNI PILIC GOGUS FILLET',
                                         'source': 'https://x/1', 'size': None,
                                         'unit_price': None, 'total': 322.0}]},
    'rice':           {'low': 45.0, 'high': 89.5, 'basis': '500 g', 'ignored': 2,
                       'observations': [{'price': 90.0, 'shop': 'PIRINC 1KG', 'source': 'https://x/2',
                                         'size': '1 KG', 'unit_price': 90.0, 'total': 45.0}]},
}


def api(route):
    url = route.request.url

    if url.endswith('/config'):
        return route.fulfill(status=200, content_type='application/json', body=json.dumps(
            {'gemini_ready': True, 'supabase_ready': True, 'admin_protected': False,
             'price_source': 'Kıbrıs Sanal Market'}))

    if url.endswith('/units'):
        return route.fulfill(status=200, content_type='application/json', body=json.dumps(
            {'units': [{'value': 'g', 'label': 'g'}, {'value': 'kg', 'label': 'kg'},
                       {'value': 'ml', 'label': 'ml'}, {'value': 'l', 'label': 'L'},
                       {'value': 'piece', 'label': 'piece'}]}))

    if url.endswith('/price'):
        body = json.loads(route.request.post_data)
        asked.append(body)
        found = PRICES.get(body['ingredient'].lower())
        if not found:
            return route.fulfill(status=404, content_type='application/json',
                                 body=json.dumps({'detail': 'مفيش منتج بيطابق'}))
        out = dict(found)
        out['ingredient'] = body['ingredient']
        out['provisional'] = False
        return route.fulfill(status=200, content_type='application/json', body=json.dumps(out))

    return route.fulfill(status=404, body='')


def url(name):
    return (W / name).as_uri()


with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    page = b.new_page(viewport={'width': 1100, 'height': 1000})
    page.on('pageerror', lambda e: console.append(f'PAGEERROR: {e}'))
    page.on('console', lambda m: console.append(f'{m.type}: {m.text}') if m.type == 'error' else None)
    page.route('**://**supabase.co/**', lambda r: r.abort())
    page.route('**/127.0.0.1:8010/**', api)

    # ================================================= 1) المحلات المبدئية ==
    print('== 1) أول فتحة ==')
    page.goto(url('settings.html'))
    page.wait_for_timeout(600)
    chips = [c.inner_text().strip() for c in page.locator('.chip').all()]
    print('   المحلات:', chips)
    check('مفيش محلات تركيا', not any(x in ' '.join(chips) for x in ['BİM', 'A101', 'Migros']), chips)
    check('فيه محلات قبرصية', any('Sanal' in c or 'Lemar' in c for c in chips), chips)
    check('سبب إخفاء زرار البحث مكتوب', page.locator('#find-why').count() == 1)

    # ======================================================== 2) الوحدات ==
    print('\n== 2) إضافة وجبة بوحدات ==')
    page.goto(url('meals.html'))
    page.wait_for_timeout(700)
    page.locator('main.page button', has_text='New meal').first.click()
    page.wait_for_timeout(300)
    page.fill('#new-meal-name', 'Chicken rice')
    page.press('#new-meal-name', 'Enter')
    page.wait_for_timeout(600)

    check('خانة الوحدة بقت select', page.locator('#ing-unit').evaluate('e => e.tagName') == 'SELECT')
    opts = page.locator('#ing-unit option').all_text_contents()
    print('   الوحدات:', opts)
    check('جاية من السيرفر', len(opts) == 6, opts)   # unit + 5

    for name, qty, unit in [('chicken breast', '1', 'kg'), ('rice', '500', 'g')]:
        page.fill('#ing-name', name)
        page.fill('#ing-qty', qty)
        page.select_option('#ing-unit', unit)
        page.press('#ing-name', 'Enter')
        page.wait_for_timeout(400)

    saved = page.evaluate("JSON.parse(localStorage.getItem('basket-data')).meals[0].ingredients")
    print('   المحفوظ:', [(i['name'], i['qty'], i['unit']) for i in saved])
    check('الوحدات اتحفظت صح', [i['unit'] for i in saved] == ['kg', 'g'],
          [i['unit'] for i in saved])

    # تعديل وحدة موجودة
    page.locator('.ing-list select').first.select_option('g')
    page.wait_for_timeout(400)
    again = page.evaluate("JSON.parse(localStorage.getItem('basket-data')).meals[0].ingredients")
    check('تعديل الوحدة بيتحفظ', again[0]['unit'] == 'g', again[0]['unit'])
    page.locator('.ing-list select').first.select_option('kg')
    page.wait_for_timeout(400)
    page.screenshot(path=str(SHOTS / 'j1-meals.png'), full_page=True)

    # ==================================================== 3) جلب الأسعار ==
    print('\n== 3) جلب الأسعار من السيرفر ==')
    page.goto(url('compare.html'))
    page.wait_for_timeout(1000)

    btn = page.locator('#ask-ai-btn')
    check('الزرار ظهر لأن السيرفر شغّال', not btn.is_hidden())
    print('   الزرار:', btn.inner_text())
    check('مكتوب عليه اسم المصدر', 'Sanal' in btn.inner_text(), btn.inner_text())

    body = page.locator('#view').inner_text()
    check('الإشارة القديمة لـ js/ai.js اختفت',
          'Open <code>js/ai.js</code>' not in page.content()
          and 'js/ai.js' not in page.locator('#view').inner_text())

    asked.clear()
    btn.click()
    page.wait_for_timeout(2500)

    print('   اللي اتبعت للسيرفر:', json.dumps(asked, ensure_ascii=False))
    check('سأل عن مكوّنين بس', len(asked) == 2, len(asked))
    check('وبعت الكمية والوحدة', asked[0].get('qty') == 1 and asked[0].get('unit') == 'kg', asked[0])
    check('مسألش عن كل محل على حدة', len(asked) == 2, 'لو 6 يبقى بيكرّر لكل محل')

    body = page.locator('#view').inner_text()
    print('  ', re.sub(r'\n+', ' | ', body)[:300])
    check('السعر اتحط', '322' in body, body[:120])
    check('والتاني كمان', '45' in body, body[:200])

    data = page.evaluate("JSON.parse(localStorage.getItem('basket-data'))")
    source = [m for m in data['markets'] if 'Sanal' in m['name']][0]
    ings = data['meals'][0]['ingredients']
    check('الأسعار راحت لعمود المصدر',
          all(source['id'] in i['prices'] for i in ings), [list(i['prices']) for i in ings])
    check('ومعلّمة إنها من الـ API',
          all(i['prices'][source['id']]['source'] == 'api' for i in ings))
    note = ings[1]['prices'][source['id']]['note']
    print('   الملاحظة:', note)
    check('المدى محفوظ في الملاحظة', 'up to' in (note or ''), note)
    tags = [x.inner_text().strip() for x in page.locator('#view .tag').all()]
    print('   العلامات:', tags)
    check('العلامة مش "you" على سعر من السيرفر',
          all(x.lower() == 'web' for x in tags), tags)
    check('والملاحظة في الـ tooltip',
          'up to' in (page.locator('#view .tag').nth(1).get_attribute('title') or ''),
          page.locator('#view .tag').nth(1).get_attribute('title'))
    page.screenshot(path=str(SHOTS / 'j2-fetched.png'), full_page=True)

    # ============================================= 4) مكوّن مش موجود ==
    print('\n== 4) مكوّن السيرفر ملقاهوش ==')
    page.goto(url('meals.html'))
    page.wait_for_timeout(800)
    page.locator('[data-open]').first.click()      # افتح الوجبة الأول
    page.wait_for_timeout(500)
    page.fill('#ing-name', 'saffron')
    page.press('#ing-name', 'Enter')
    page.wait_for_timeout(500)

    page.goto(url('compare.html'))
    page.wait_for_timeout(1000)
    page.locator('#ask-ai-btn').click()
    page.wait_for_timeout(2000)
    body = page.locator('#view').inner_text()
    check('بيقول إن المكوّن ده فشل', 'بيطابق' in body or 'مفيش' in body or 'add price' in body,
          body[:200])
    check('والباقي فضل محطوط', '322' in body)
    page.screenshot(path=str(SHOTS / 'j3-missing.png'), full_page=True)

    # ===================================================== 5) الداشبورد ==
    print('\n== 5) الداشبورد ==')
    page.goto(url('index.html'))
    page.wait_for_timeout(800)
    body = page.locator('main.page').inner_text()
    print('  ', re.sub(r'\n+', ' | ', body.split('Settings')[-1])[:260])
    check('مش بيقول "no prices yet" وفيه أسعار', 'no prices yet' not in body, body[:200])
    check('بيقول كام مكوّن اتسعّر', 'priced' in body.lower(), body[:200])
    check('العدّاد بقى "fully priced"', 'fully priced' in body.lower(), body[:200])
    page.screenshot(path=str(SHOTS / 'j4-dashboard.png'), full_page=True)

    # ========================================================= 6) اللعبة ==
    print('\n== 6) اللعبة ==')
    page.goto(url('game.html'))
    page.wait_for_timeout(800)
    body = page.locator('main.page').inner_text()
    check('اللعبة بتشتغل', page.locator('.choice').count() >= 2,
          page.locator('.choice').count())
    page.screenshot(path=str(SHOTS / 'j5-game.png'), full_page=True)

    # ============================================= 7) السيرفر مش شغّال ==
    print('\n== 7) السيرفر مقفول ==')
    page.unroute('**/127.0.0.1:8010/**')
    page.route('**/127.0.0.1:8010/**', lambda r: r.abort('connectionrefused'))
    page.goto(url('compare.html'))
    page.wait_for_timeout(1200)
    check('الزرار اتخفى', page.locator('#ask-ai-btn').is_hidden())
    body = page.locator('#view').inner_text()
    check('وقال لليوزر يعمل إيه', 'uvicorn' in body, body[-200:])
    check('والأسعار المحفوظة لسه موجودة', '322' in body)

    page.goto(url('meals.html'))
    page.wait_for_timeout(900)
    page.locator('[data-open]').first.click()
    page.wait_for_timeout(600)
    check('الوحدات لسه شغّالة من غير سيرفر',
          page.locator('#ing-unit option').count() == 6,
          page.locator('#ing-unit option').count())

    # ========================================================= 8) موبايل ==
    print('\n== 8) الموبايل ==')
    page.set_viewport_size({'width': 390, 'height': 844})
    for name in ['index.html', 'meals.html', 'compare.html', 'settings.html', 'game.html']:
        page.goto(url(name))
        page.wait_for_timeout(500)
        over = page.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(f'{name}: مفيش سكرول أفقي', over <= 0, f'{over}px')
    page.screenshot(path=str(SHOTS / 'j6-mobile.png'), full_page=True)

    b.close()

print('\n== console ==')
real = [c for c in dict.fromkeys(console)
        if 'ERR_CONNECTION_REFUSED' not in c and 'Failed to load resource' not in c]
print('  ', '\n   '.join(real) if real else 'ok   مفيش أخطاء')

print('\n' + ('ALL PASSED' if not failures and not real else f'PROBLEMS: {failures} {real}'))
sys.exit(1 if failures or real else 0)
