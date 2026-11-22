# Tests for the board view, follow-up reminders, material planning, calendar,
# job sheets and backup — run against fake-supabase.js (no real data touched).
import asyncio, json, pathlib, datetime
from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).resolve().parent
html = (HERE.parent / 'solar_business_app.html').read_text(encoding='utf-8')
html = html.replace('<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>', '<script src="fake-supabase.js"></script>')
TEST = HERE / 'app_under_test.html'; TEST.write_text(html, encoding='utf-8')

today = datetime.date.today()
ago = lambda n: (today - datetime.timedelta(days=n)).isoformat()
ahead = lambda n: (today + datetime.timedelta(days=n)).isoformat()

SEED = f"""
__db.customers = [
  {{id:1,name:'Asha Lead',city:'Puri',category:'1KW',price:65000,priority:'Medium',stage_index:0,stage_dates:{{lead:'{ago(10)}'}},app_no:'PMGSY-2026-0001',work_order_no:''}},
  {{id:2,name:'Bina Approved',city:'Cuttack',phone:'98765 43210',category:'1KW',price:65000,priority:'High',stage_index:5,stage_dates:{{lead:'{ago(30)}',approved:'{ago(1)}'}},app_no:'PMGSY-2026-0002',work_order_no:''}},
  {{id:3,name:'Chitra Paid',city:'Bhubaneswar',category:'1KW',price:65000,priority:'Low',stage_index:7,stage_dates:{{lead:'{ago(40)}',approved:'{ago(20)}',paid:'{ago(2)}'}},app_no:'PMGSY-2026-0003',work_order_no:'WO-2026-0001'}},
  {{id:4,name:'Dev Connected',city:'Puri',category:'3KW',price:185000,priority:'Medium',stage_index:10,stage_dates:{{lead:'{ago(60)}',installed:'{ago(20)}',connected:'{ago(0)}'}},app_no:'PMGSY-2026-0004',work_order_no:'WO-2026-0002'}}
];
__db.teams = [{{id:1,name:'Team 1',zone:'Puri',electrician:'Karthik',electrician_phone:'+91 90000 00001',helper:'Basu',helper_phone:''}},{{id:2,name:'Team 2',zone:'Cuttack'}}];
__db.inventory = [{{id:10,name:'450W Panel',category:'Panel',stock:4,reorder:1,cost:15000}},{{id:11,name:'1KW Inverter',category:'Inverter',stock:5,reorder:1,cost:20000}}];
__db.app_settings[0].category_bom = {{'1KW':[{{itemId:10,qty:3}},{{itemId:11,qty:1}}],'3KW':[],'5KW':[]}};
__db.assignments = [
  {{id:50,customer_id:3,team_id:1,date:'{ahead(2)}',status:'Scheduled',notes:'Roof access via back stairs'}},
  {{id:51,customer_id:4,team_id:1,date:'{ahead(2)}',status:'Completed',stock_deducted:true}}
];
"""

results = []
def check(name, ok, detail=''):
    results.append(ok); print(('PASS ' if ok else 'FAIL ') + name + (f'  [{detail}]' if detail and not ok else ''))

async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(); ctx = await b.new_context(accept_downloads=True); pg = await ctx.new_page()
    errs, dialogs = [], []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    state = {'answer': True}
    async def ond(d):
      dialogs.append(d.message)
      if d.type == 'prompt': await d.accept('Test Device')
      elif state['answer']: await d.accept()
      else: await d.dismiss()
    pg.on('dialog', lambda d: asyncio.ensure_future(ond(d)))
    await pg.goto(TEST.as_uri()); await pg.wait_for_timeout(500)
    await pg.evaluate(SEED + "loadAllData().then(renderEverything)"); await pg.wait_for_timeout(300)

    # 1 board view
    await pg.evaluate("setPipelineView('board')")
    cols = await pg.evaluate("document.querySelectorAll('#pipelineBoard .board-col').length")
    check('board shows 11 stage columns', cols == 11, cols)
    col0 = await pg.evaluate("[...document.querySelectorAll('.board-col[data-stage=\"0\"] .bname')].map(e=>e.textContent)")
    check('lead card in first column', col0 == ['Asha Lead'], col0)
    check('table hidden in board view', await pg.evaluate("document.getElementById('pipelineTableWrap').style.display") == 'none')

    # 2 follow-up reminders
    stuck = await pg.evaluate("stuckInfo(customers.find(c=>c.id===1))")
    check('lead waiting 10 days is follow-up due', bool(stuck) and stuck['days'] == 10, stuck)
    check('recent approval is not due', await pg.evaluate("stuckInfo(customers.find(c=>c.id===2))") is None)
    att = await pg.evaluate("document.getElementById('attentionList').textContent")
    check('needs attention lists the follow-up', 'Asha Lead' in att and 'send a price quote' in att, att[:200])

    # 3 material planning: Chitra (scheduled first) gets 3 of 4 panels, Bina is short 2
    plan = await pg.evaluate("(()=>{const p=materialPlan(); return {need:p.need, bina:p.perCustomer[2].shortages.map(s=>[s.item.name,s.qty]), chitra:p.perCustomer[3].shortages.length, dev: 4 in p.perCustomer}})()")
    check('reserved panels = 6', plan['need'].get('10') == 6, plan)
    check('scheduled job gets stock first', plan['chitra'] == 0, plan)
    check('later job shows shortage of 2 panels', plan['bina'] == [['450W Panel', 2]], plan)
    check('installed/connected job reserves nothing', plan['dev'] is False, plan)
    inv = await pg.evaluate("[...document.querySelectorAll('#invBody tr')[0].cells].map(c=>c.innerText.trim())")
    check('inventory shows reserved 6 and free -2', inv[3] == '6' and inv[4] == '-2', inv)
    mat = await pg.evaluate("document.getElementById('materialNeeds').innerText")
    check('dashboard material table shows the shortage', '450W Panel' in mat and 'Reorder' in mat, mat)

    # 4 move lead to Approved via board -> saved + shortage alert
    dialogs.clear()
    await pg.evaluate("moveCustomerToStage(1, 5)"); await pg.wait_for_timeout(300)
    row = await pg.evaluate("__db.customers.find(c=>c.id===1)")
    check('move writes stage to database', row['stage_index'] == 5 and row['stage_dates'].get('approved') == today.isoformat(), row)
    check('approval with no stock left alerts shortage', any('Material is short' in d for d in dialogs), dialogs)

    # 5 move backwards, user cancels -> unchanged
    state['answer'] = False
    await pg.evaluate("moveCustomerToStage(1, 2)"); await pg.wait_for_timeout(200)
    check('cancelled backward move leaves stage', await pg.evaluate("__db.customers.find(c=>c.id===1).stage_index") == 5)
    state['answer'] = True

    # 6 drop on Work Order Created without a WO -> Create WO flow
    await pg.evaluate("moveCustomerToStage(1, 6)"); await pg.wait_for_timeout(300)
    row = await pg.evaluate("__db.customers.find(c=>c.id===1)")
    check('work order stage creates the WO number', row['stage_index'] == 6 and row['work_order_no'].startswith('WO-'), row)

    # 7 move to Payment Received -> offers assignment, opens assign tab
    dialogs.clear()
    await pg.evaluate("moveCustomerToStage(1, 7)"); await pg.wait_for_timeout(400)
    check('payment offers to assign a team', any('Assign a team' in d for d in dialogs), dialogs)
    check('assign form opened for that customer', await pg.evaluate("document.getElementById('assign').style.display==='block' && Number(document.getElementById('assignCustomer').value)") == 1)

    # 8 failed write rolls back
    await pg.evaluate("__expired=true; __refreshFails=true")
    await pg.evaluate("moveCustomerToStage(2, 6)"); await pg.wait_for_timeout(300)
    check('failed move rolls back', await pg.evaluate("customers.find(c=>c.id===2).stageIndex") == 5)
    await pg.evaluate("__expired=false; __refreshFails=false")

    # 9 assignment checks: same team same date
    await pg.evaluate("openAssignForm(2)")
    await pg.select_option('#assignTeam', '1'); await pg.fill('#assignDate', ahead(2)); await pg.dispatch_event('#assignDate', 'change')
    chk = await pg.evaluate("document.getElementById('assignChecks').innerText")
    check('double-booking warning shown', 'already has 1 installation' in chk, chk)
    check('material shortage shown on form', 'Material short' in chk, chk)

    # 10 calendar
    await pg.evaluate("setAssignView('calendar')")
    chips = await pg.evaluate("[...document.querySelectorAll('#calGrid .cal-chip')].map(c=>[c.textContent,c.classList.contains('clash')])")
    check('calendar shows scheduled jobs', any('Chitra Paid' in c[0] for c in chips), chips)
    check('completed/other jobs not marked clash wrongly', all(not c[1] for c in chips), chips)

    # 11 save new assignment -> offers job sheet
    dialogs.clear()
    await pg.evaluate("openAssignForm(2)"); await pg.select_option('#assignTeam', '1'); await pg.fill('#assignDate', ahead(2))
    await pg.evaluate("saveAssignment()"); await pg.wait_for_timeout(400)
    check('new assignment offers to send job sheet', any('Send the job sheet' in d for d in dialogs), dialogs)
    check('job sheet modal open', await pg.evaluate("document.getElementById('sendOverlay').classList.contains('open')"))
    text = await pg.input_value('#sendText')
    check('job sheet has customer, phone and material', 'Bina Approved' in text and '98765 43210' in text and '3 × 450W Panel' in text, text)
    btns = await pg.evaluate("[...document.querySelectorAll('#sendButtons button')].map(b=>b.getAttribute('onclick'))")
    check('WhatsApp button uses electrician number with 91', any("'919000000001'" in (x or '') for x in btns), btns)
    clash = await pg.evaluate("[...document.querySelectorAll('#calGrid .cal-chip.clash')].length")
    check('calendar now flags the double booking', clash == 2, clash)
    await pg.evaluate("closeModal('sendOverlay')")

    # 12 dashboard month stats
    month = await pg.evaluate("document.getElementById('statCardsMonth').innerText")
    check('dashboard month cards render', 'Installed This Month' in month and 'Avg. Lead' in month and '60 days' in month, month)

    # 13 backup download
    async with pg.expect_download() as dl:
      await pg.evaluate("downloadBackup()")
    d = await dl.value; path = await d.path()
    data = json.loads(pathlib.Path(path).read_text())
    check('backup has every table', sorted(data['tables']) == sorted(['customers','teams','assignments','inventory','inventory_movements','crew','payroll_records','app_settings']), list(data['tables']))
    check('backup has all customers', len(data['tables']['customers']) == 4)
    check('backup file name', d.suggested_filename == f'solarops-backup-{today.isoformat()}.json', d.suggested_filename)

    # 14 table view still works
    await pg.evaluate("setPipelineView('table')")
    rows = await pg.evaluate("document.querySelectorAll('#custBody tr').length")
    check('table view still lists customers', rows == 4, rows)

    check('no page errors', not errs, errs)
    await b.close()
  TEST.unlink()
  print(f"\n{sum(results)}/{len(results)} passed")

asyncio.run(main())
