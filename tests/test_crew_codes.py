# Crew employee-code tests (Staff = E001…, Workman = W001…) against fake-supabase.js.
import asyncio, pathlib
from playwright.async_api import async_playwright
HERE = pathlib.Path(__file__).resolve().parent
html = (HERE.parent / 'solar_business_app.html').read_text(encoding='utf-8')
html = html.replace('<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>', '<script src="fake-supabase.js"></script>')
TEST = HERE / 'app_under_test.html'; TEST.write_text(html, encoding='utf-8')
async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(); pg = await b.new_page(); errs=[]; dialogs=[]
    pg.on('pageerror', lambda e: errs.append(str(e)))
    async def ond(d): dialogs.append(d.message); await d.accept('Test Device')
    pg.on('dialog', lambda d: asyncio.ensure_future(ond(d)))
    await pg.goto(TEST.as_uri()); await pg.wait_for_timeout(600)
    st = "({open:document.getElementById('crewOverlay').classList.contains('open'), err:document.getElementById('crewError').textContent, code:document.getElementById('crewEmpCode').value, db:__db.crew.map(c=>[c.name,c.emp_category||'',c.emp_code||''])})"
    async def add(name, cat, setup='0', code=None):
      await pg.evaluate('openCrewModal()')
      if cat: await pg.select_option('#crewCategory', cat)
      shown = await pg.input_value('#crewEmpCode')
      if code is not None: await pg.fill('#crewEmpCode', code)
      await pg.fill('#crewName', name); await pg.evaluate(setup)
      await pg.click('#crewSaveBtn'); await pg.wait_for_timeout(300)
      r = await pg.evaluate(st); r['shown']=shown; return r
    def show(label, r): print(f"{label:34} shown={r['shown']!r:8} open={r['open']} err={r['err']!r}")
    show('1 no category', await add('Nobody', ''))
    await pg.evaluate("closeModal('crewOverlay')")
    show('2 first staff', await add('Staff One', 'Staff'))
    show('3 second staff', await add('Staff Two', 'Staff'))
    show('4 first workman', await add('Work One', 'Workman'))
    show('5 typed dup code', await add('Dup', 'Workman', code='e001'))
    await pg.evaluate("closeModal('crewOverlay')")
    show('6 other device took W002', await add('Work Two', 'Workman', setup="__db.crew.push({id:500,name:'Remote',emp_category:'Workman',emp_code:'W002'})"))
    print('   note:', dialogs[-1] if dialogs else None)
    # edit existing crew without code -> assign category
    await pg.evaluate("editCrew(1)"); await pg.select_option('#crewCategory','Workman')
    shown = await pg.input_value('#crewEmpCode'); await pg.click('#crewSaveBtn'); await pg.wait_for_timeout(300)
    print(f"{'7 edit old crew -> Workman':34} shown={shown!r}")
    # edit keeps code when category unchanged
    await pg.evaluate("editCrew(crewList.find(c=>c.name==='Staff One').id)")
    print(f"{'8 edit keeps code':34} shown={await pg.input_value('#crewEmpCode')!r}")
    await pg.fill('#crewName','Staff One Renamed'); await pg.click('#crewSaveBtn'); await pg.wait_for_timeout(300)
    # migration missing
    show('9 migration not run', await add('Pre Migration', 'Staff', setup='__noEmpCols=true'))
    await pg.evaluate("__noEmpCols=false; closeModal('crewOverlay')")
    print('table codes:', await pg.evaluate("[...document.querySelectorAll('#crewBody tr td:first-child strong')].map(e=>e.textContent)"))
    print('db:', await pg.evaluate("__db.crew.map(c=>[c.name,c.emp_category||'',c.emp_code||''])"))
    print('errors', errs); await b.close()
  TEST.unlink()
asyncio.run(main())
