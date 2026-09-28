import asyncio, pathlib
from playwright.async_api import async_playwright
# Login-screen tests: simulates blocked library downloads and a blocked database.
# Needs the real library once: `npm i @supabase/supabase-js@2` inside tests/.
HERE = pathlib.Path(__file__).resolve().parent
UMD = (HERE / 'node_modules/@supabase/supabase-js/dist/umd/supabase.js').read_text()
HTML = (HERE.parent / 'solar_business_app.html').read_text()
async def run(name, jsdelivr, unpkg, supa):
  async with async_playwright() as p:
    b = await p.chromium.launch(); pg = await b.new_page(); errs=[]
    pg.on('pageerror', lambda e: errs.append(str(e)))
    async def route(r):
      u = r.request.url
      if u.startswith('https://solar.test/'):
        return await r.fulfill(body=HTML, content_type='text/html') if u.endswith('.html') else await r.fulfill(status=404, body='')
      if 'cdn.jsdelivr.net' in u: return await (r.fulfill(body=UMD, content_type='application/javascript') if jsdelivr else r.abort())
      if 'unpkg.com' in u: return await (r.fulfill(body=UMD, content_type='application/javascript') if unpkg else r.abort())
      if 'supabase.co' in u:
        if supa=='block': return await r.abort()
        if supa=='badpw': return await r.fulfill(status=400, content_type='application/json', body='{"error":"invalid_grant","error_description":"Invalid login credentials","code":"invalid_credentials","msg":"Invalid login credentials"}')
      return await r.abort()
    await pg.route('**/*', route)
    await pg.goto('https://solar.test/solar_business_app.html'); await pg.wait_for_timeout(1500)
    before = await pg.evaluate("document.getElementById('loginError').textContent")
    await pg.fill('#loginPassword','x'); await pg.click('text=Log In'); await pg.wait_for_timeout(2500)
    after = await pg.evaluate("document.getElementById('loginError').textContent")
    print(f'{name:28} lib={await pg.evaluate("!!window.supabase")} | on load: {before!r}\n{"":28} after login: {after!r} | pageerrors={errs}')
    await b.close()
async def main():
  await run('A jsdelivr ok, db ok(badpw)', True, True, 'badpw')
  await run('B jsdelivr blocked->unpkg', False, True, 'badpw')
  await run('C both CDNs blocked', False, False, 'badpw')
  await run('D db (supabase.co) blocked', True, True, 'block')
asyncio.run(main())
