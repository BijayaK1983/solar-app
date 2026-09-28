import asyncio, json, pathlib, re
# Builds a test copy of the app that talks to fake-supabase.js instead of the real database.
HERE = pathlib.Path(__file__).resolve().parent
APP = HERE.parent / 'solar_business_app.html'
TEST = HERE / 'app_under_test.html'
html = APP.read_text(encoding='utf-8')
html = html.replace('<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>', '<script src="fake-supabase.js"></script>')
TEST.write_text(html, encoding='utf-8')
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(); pg = await b.new_page()
    errs=[]; dialogs=[]
    pg.on('pageerror', lambda e: errs.append('PAGEERROR: '+str(e)))
    async def ond(d): dialogs.append(d.message); await d.accept('Test Mac')
    pg.on('dialog', lambda d: asyncio.ensure_future(ond(d)))
    await pg.goto(TEST.as_uri()); await pg.wait_for_timeout(600)
    async def add(name, setup='', dbl=False):
      await pg.evaluate("openCustomerModal()")
      await pg.fill('#custName',name); await pg.fill('#custCity','Test City')
      await pg.check('input[name="custCategory"][value="3KW"]', force=True)
      await pg.evaluate(setup or '0')
      await (pg.evaluate('saveCustomer()') if dbl else pg.click('#custSaveBtn'))
      if dbl: await pg.evaluate("saveCustomer()")
      await pg.wait_for_timeout(500)
      return await pg.evaluate("({open:document.getElementById('custOverlay').classList.contains('open'), err:document.getElementById('custError').textContent, btn:document.getElementById('custSaveBtn').textContent, disabled:document.getElementById('custSaveBtn').disabled, n:__db.customers.length})")
    print('1 normal  ', await add('Test Customer'))
    print('2 expired ', await add('Expired Ok', "__expired=true"), 'refreshed', await pg.evaluate('__refreshed'))
    print('3 exp+fail', await add('Expired Fail', "__expired=true; __refreshFails=true"))
    await pg.evaluate("__expired=false; __refreshFails=false")
    await pg.evaluate("closeModal('custOverlay')")
    print('4 network ', await add('Net Down', "__throw=true"))
    await pg.evaluate("__throw=false; closeModal('custOverlay')")
    print('5 manual dup', await add('Dup', "document.getElementById('custAppNo').value='PMGSY-2026-0008'"))
    await pg.evaluate("closeModal('custOverlay')")
    print('6 stale auto', await add('Stale', "__db.customers.push({id:999,name:'Other device',app_no:document.getElementById('custAppNo').value})"), dialogs[-1])
    print('7 double-click', await add('Double', '', dbl=True))
    # edit existing
    await pg.evaluate("openCustomerModal(customers.find(c=>c.name==='Test Customer'))")
    await pg.fill('#custCity','Edited City'); await pg.click('#custSaveBtn'); await pg.wait_for_timeout(400)
    print('8 edit', await pg.evaluate("[__db.customers.find(c=>c.name==='Test Customer').city, customers.find(c=>c.name==='Test Customer').city, document.getElementById('custOverlay').classList.contains('open')]"))
    # edit failing leaves local data untouched
    await pg.evaluate("openCustomerModal(customers.find(c=>c.name==='Test Customer'))")
    await pg.fill('#custCity','Other City'); await pg.evaluate("__throw=true"); await pg.click('#custSaveBtn'); await pg.wait_for_timeout(400)
    print('9 edit fail', await pg.evaluate("[customers.find(c=>c.name==='Test Customer').city, document.getElementById('custError').textContent]"))
    print('names', [r['name'] for r in await pg.evaluate('__db.customers')])
    print('errors', errs)
    await b.close()
asyncio.run(main())
