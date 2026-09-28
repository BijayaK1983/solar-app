(function(){
  const db = { customers:[
    {id:1,name:'Sample Customer',app_no:'PMGSY-2026-0008',work_order_no:'',stage_index:0,stage_dates:{},category:'1KW',price:100000,priority:'Medium'}],
    teams:[],inventory:[],inventory_movements:[],crew:[],payroll_records:[],assignments:[],app_settings:[{id:1,category_prices:{'1KW':70000,'3KW':195000,'5KW':300000},category_bom:{'1KW':[],'3KW':[],'5KW':[]}}]};
  window.__db = db; window.__log = [];
  window.__unique = true;
  let nextId = 100;
  function q(table){
    const st = {table, op:'select', filters:[], row:null, single:false, maybe:false, sel:false};
    const b = {
      select(){ if(st.op==='select') st.op='select'; st.sel=true; return b; },
      insert(row){ st.op='insert'; st.row=row; return b; },
      update(row){ st.op='update'; st.row=row; return b; },
      upsert(row){ st.op='upsert'; st.row=row; return b; },
      delete(){ st.op='delete'; return b; },
      eq(c,v){ st.filters.push(r=>r[c]==v); return b; },
      ilike(c,p){ const re=new RegExp('^'+p.replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/%/g,'.*')+'$','i'); st.filters.push(r=>re.test(r[c]||'')); return b; },
      order(){ return b; }, limit(){ return b; },
      single(){ st.single=true; return b; }, maybeSingle(){ st.maybe=true; return b; },
      then(res, rej){ return new Promise(r=>r(run())).then(res, rej); }
    };
    function dup(row, id){
      if(!window.__unique || table!=='customers') return null;
      for(const col of ['app_no','work_order_no']){
        const v=(row[col]||'').trim().toUpperCase();
        if(v && db.customers.some(r=>r.id!==id && (r[col]||'').trim().toUpperCase()===v))
          return {code:'23505', message:`duplicate key value violates unique constraint "customers_${col}_unique"`};
      }
      return null;
    }
    function run(){
      if(window.__throw && st.op!=='select') throw new TypeError('Failed to fetch');
      if(window.__expired && st.op!=='select') return {data:null,error:{code:'PGRST303',message:'JWT expired'}};
      window.__log.push({table, op:st.op, row:st.row});
      const rows = db[table] || (db[table]=[]);
      const match = rows.filter(r=>st.filters.every(f=>f(r)));
      if(st.op==='insert'){ const e=dup(st.row); if(e) return {data:null,error:e}; const r={...st.row,id:nextId++}; rows.push(r); return {data: st.single? r : [r], error:null}; }
      if(st.op==='update'){ for(const r of match){ const e=dup({...r,...st.row}, r.id); if(e) return {data:null,error:e}; } match.forEach(r=>Object.assign(r,st.row)); return {data: st.single? match[0]: match, error:null}; }
      if(st.op==='delete'){ db[table]=rows.filter(r=>!match.includes(r)); return {data:null,error:null}; }
      if(st.op==='upsert'){ return {data:st.row,error:null}; }
      if(st.single||st.maybe) return {data: match[0]||null, error: (st.single&&!match[0])?{message:'no rows'}:null};
      return {data: match.map(r=>({...r})), error:null};
    }
    return b;
  }
  const ch = { on(){ return ch; }, subscribe(){ return ch; } };
  window.supabase = { createClient(){ return {
    from: q,
    channel(){ return ch; },
    auth: { getSession: async()=>({data:{session:{user:{email:'team@x'}}}}), signInWithPassword: async()=>({data:{},error:null}), signOut: async()=>({}), refreshSession: async()=>{ window.__refreshed=(window.__refreshed||0)+1; window.__expired=false; return {data:{},error: window.__refreshFails?{message:'refresh failed'}:null}; }, onAuthStateChange(){ return {data:{subscription:{unsubscribe(){}}}}; } }
  }; } };
})();
