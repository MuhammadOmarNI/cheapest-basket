"""
اختبار إن صفحة الأدمن اتفصلت فعلاً عن التطبيق.

اللي بنتأكد منه: اليوزر العادي ما يشوفش أي أثر ليها في أي صفحة.
"""
from playwright.sync_api import sync_playwright
import pathlib, sys

W = pathlib.Path('/tmp/claude-0/-home-claude/08902a29-63c7-5eb8-bfbc-14187226ca0e/scratchpad/adm')

failures, errors = [], []


def check(label, cond, detail=''):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + ('' if cond else f'  {detail}'))
    if not cond:
        failures.append(label)


APP_PAGES = ['index.html', 'meals.html', 'compare.html', 'game.html', 'settings.html']

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    page = b.new_page(viewport={'width': 1000, 'height': 900})
    page.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
    page.on('console', lambda m: errors.append(f'{m.type}: {m.text}') if m.type == 'error' else None)

    print('== صفحات التطبيق ==')
    for name in APP_PAGES:
        page.goto((W / name).as_uri())
        page.wait_for_timeout(350)

        nav = page.locator('.nav')
        links = [a.inner_text().strip() for a in page.locator('.nav-link').all()]
        html = page.content()

        ok = (nav.count() == 1
              and len(links) == 5
              and not any('admin' in l.lower() for l in links)
              and 'admin.html' not in html)
        check(f'{name}: 5 لينكات ومفيش أدمن', ok, f'{links}')

    print('\n== صفحة الأدمن ==')
    page.goto((W / 'admin.html').as_uri())
    page.wait_for_timeout(500)

    check('مفيش nav', page.locator('.nav').count() == 0)
    check('مفيش nav-link', page.locator('.nav-link').count() == 0)
    check('شريط بسيط', page.locator('.topbar-bare').count() == 1)
    check('العنوان Admin', 'Admin' in page.locator('.topbar-bare .brand').inner_text())

    back = page.locator('.topbar-bare a.where')
    check('لينك الرجوع للتطبيق', back.get_attribute('href') == 'index.html',
          back.get_attribute('href'))

    # الصفحة مابتحمّلش data.js ولا ai.js
    html = page.content()
    check('مش محمّلة data.js', 'js/data.js' not in html)
    check('مش محمّلة ai.js', 'js/ai.js' not in html)
    check('DB مش موجود خالص', page.evaluate("typeof window.DB") == 'undefined')
    check('AUTH موجود (محتاجينه للـ token)', page.evaluate("typeof window.AUTH") == 'object')

    print('\n== عرض الموبايل ==')
    page.set_viewport_size({'width': 390, 'height': 850})
    page.wait_for_timeout(300)
    over = page.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
    check('مفيش سكرول أفقي', over <= 0, f'بيزيد {over}px')
    page.screenshot(path=str(W / '../admin-separate-mobile.png'), full_page=False)

    page.set_viewport_size({'width': 1000, 'height': 900})
    page.wait_for_timeout(300)
    page.screenshot(path=str(W / '../admin-separate.png'), full_page=False)

    b.close()

print('\n== console ==')
# صفحة الأدمن بتحاول تكلّم 127.0.0.1:8010 اللي مش شغّال هنا — متوقع
errors = [e for e in errors if 'ERR_CONNECTION_REFUSED' not in e and 'Failed to load resource' not in e]
print('  ', '\n   '.join(errors) if errors else 'ok   مفيش أخطاء')

print('\n' + ('ALL PASSED' if not failures and not errors else f'PROBLEMS: {failures} {errors}'))
sys.exit(1 if failures or errors else 0)
