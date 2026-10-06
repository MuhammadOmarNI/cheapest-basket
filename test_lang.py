"""
اختبار مبدّل اللغة على اللغات الستة.

المهم مش إن الترجمة موجودة — المهم إنها بتوصل للشاشة فعلاً، وإن
الاختيار بيفضل محفوظ، وإن العربي بيقلب الاتجاه.
"""
from playwright.sync_api import sync_playwright
import pathlib, shutil, sys

SRC = pathlib.Path('/mnt/user-data/outputs/basket')
W = pathlib.Path('/tmp/claude-0/-home-claude/08902a29-63c7-5eb8-bfbc-14187226ca0e/scratchpad/lang')
SHOTS = W.parent / 'shots3'

failures, console = [], []


def check(label, cond, detail=''):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + ('' if cond else f'  {detail}'))
    if not cond:
        failures.append(label)


if W.exists():
    shutil.rmtree(W)
shutil.copytree(SRC, W)
SHOTS.mkdir(exist_ok=True)

# نص متوقّع في كل لغة: (كود, اسم القايمة, كلمة لازم تظهر في الـ nav)
EXPECT = [
    ('en', 'English',   'Compare',      'ltr'),
    ('ar', 'العربية',   'المقارنة',      'rtl'),
    ('tr', 'Türkçe',    'Karşılaştır',  'ltr'),
    ('sw', 'Kiswahili', 'Linganisha',   'ltr'),
    ('zh', '中文',       '比较',          'ltr'),
    ('ru', 'Русский',   'Сравнить',     'ltr'),
]

PAGES = ['index.html', 'meals.html', 'compare.html', 'game.html', 'settings.html']


def url(name):
    return (W / name).as_uri()


with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    page = b.new_page(viewport={'width': 1000, 'height': 900})
    page.on('pageerror', lambda e: console.append(f'PAGEERROR: {e}'))
    page.on('console', lambda m: console.append(f'{m.type}: {m.text}') if m.type == 'error' else None)
    page.route('**://**supabase.co/**', lambda r: r.abort())
    page.route('**/127.0.0.1:8010/**', lambda r: r.abort())

    # ============================================================= الشريط ==
    print('== الشريط نفسه ==')
    page.goto(url('index.html'))
    page.wait_for_timeout(600)

    bar = page.locator('.langbar')
    check('الشريط موجود', bar.count() == 1)
    box = bar.bounding_box()
    print(f"   مكانه: x={box['x']:.0f} y={box['y']:.0f}  حجمه: {box['width']:.0f}×{box['height']:.0f}")
    check('فوق على الشمال', box['x'] < 60 and box['y'] < 60, box)
    check('صغير', box['width'] < 170 and box['height'] < 40, box)

    opts = page.locator('#lang-select option').all_text_contents()
    print('   اللغات:', opts)
    check('ست لغات', len(opts) == 6, opts)
    check('بالترتيب المطلوب',
          opts == ['English', 'العربية', 'Türkçe', 'Kiswahili', '中文', 'Русский'], opts)

    # ========================================================= كل لغة ==
    for code, label, navword, direction in EXPECT:
        print(f'\n== {label} ({code}) ==')
        page.goto(url('index.html'))
        page.wait_for_timeout(400)
        page.select_option('#lang-select', code)
        page.wait_for_timeout(800)          # set() بيعمل reload

        check('الاختيار فضل محفوظ', page.locator('#lang-select').input_value() == code,
              page.locator('#lang-select').input_value())
        check('اتجاه الصفحة صح',
              page.evaluate("document.documentElement.getAttribute('dir')") == direction,
              page.evaluate("document.documentElement.getAttribute('dir')"))
        check('lang attribute صح',
              page.evaluate("document.documentElement.getAttribute('lang')") == code)

        nav = page.locator('.nav').inner_text()
        check(f'الـ nav مترجم ({navword})', navword in nav, nav.replace('\n', ' '))

        # الترجمة بتفضل على كل الصفحات
        for name in PAGES[1:]:
            page.goto(url(name))
            page.wait_for_timeout(400)
            n = page.locator('.nav').inner_text()
            if navword not in n:
                check(f'{name} مترجمة', False, n.replace('\n', ' '))
        check('كل الصفحات مترجمة', True)

        # مفيش مفاتيح ظاهرة لليوزر
        page.goto(url('settings.html'))
        page.wait_for_timeout(500)
        body = page.locator('body').inner_text()
        leaked = [w for w in body.split() if '.' in w and w.split('.')[0] in
                  ('nav', 'chrome', 'dash', 'meals', 'cmp', 'game', 'set', 'log')]
        check('مفيش مفاتيح ترجمة ظاهرة', not leaked, leaked[:4])

        page.screenshot(path=str(SHOTS / f'lang-{code}.png'), full_page=False)

    # ================================================= الرجوع للإنجليزي ==
    print('\n== الرجوع ==')
    page.goto(url('index.html'))
    page.wait_for_timeout(400)
    page.select_option('#lang-select', 'en')
    page.wait_for_timeout(800)
    check('رجع إنجليزي', 'Compare' in page.locator('.nav').inner_text())
    check('والاتجاه رجع ltr',
          page.evaluate("document.documentElement.getAttribute('dir')") == 'ltr')

    # ====================================================== عربي + موبايل ==
    print('\n== عربي على الموبايل ==')
    page.select_option('#lang-select', 'ar')
    page.wait_for_timeout(800)
    page.set_viewport_size({'width': 390, 'height': 844})
    for name in PAGES:
        page.goto(url(name))
        page.wait_for_timeout(450)
        over = page.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(f'{name}: مفيش سكرول أفقي', over <= 0, f'{over}px')
        # الشريط ما يغطّيش الهيدر
        bar = page.locator('.langbar').bounding_box()
        head = page.locator('.topbar').bounding_box()
        if bar and head:
            check(f'{name}: الشريط مش فوق الهيدر', bar['y'] + bar['height'] <= head['y'] + 4,
                  f"bar={bar['y']+bar['height']:.0f} head={head['y']:.0f}")
    page.screenshot(path=str(SHOTS / 'lang-ar-mobile.png'), full_page=False)

    b.close()

print('\n== console ==')
real = [c for c in dict.fromkeys(console) if 'Failed to load resource' not in c]
print('  ', '\n   '.join(real) if real else 'ok   مفيش أخطاء')

print('\n' + ('ALL PASSED' if not failures and not real else f'PROBLEMS: {failures} {real}'))
sys.exit(1 if failures or real else 0)
