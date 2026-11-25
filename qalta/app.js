/* =========================================================
   Qalta – бизнес дәптері (клиника, стоматология, СТО, дүкен…)
   Барлық дерек осы телефонда сақталады (localStorage).
   Бөлімдер: ҮЛГІЛЕР · ДЕРЕК · КӨМЕКШІЛЕР · КІРУ · ЭКРАНДАР · ЕСЕП · БАПТАУ
   ========================================================= */
(() => {
'use strict';

/* ---------------- ҮЛГІЛЕР (бизнес түрлері) ----------------
   role level: owner = бәрін көреді, admin = клиент/қабылдау/шығыс, staff = тек өзінікі */
const BIZ = {
  dental: { e:'🦷', n:'Стоматология', client:'Пациент', roles:{owner:'Директор', admin:'Администратор', staff:'Стоматолог'},
    services:[['Кеңес',5000],['Тіс тазалау',15000],['Пломба',20000],['Тіс жұлу',12000],['Канал емдеу',35000],['Коронка',60000],['Имплант',250000]] },
  clinic: { e:'🏥', n:'Клиника', client:'Пациент', roles:{owner:'Директор', admin:'Администратор', staff:'Дәрігер'},
    services:[['Кеңес',7000],['Талдау',4000],['УЗИ',8000],['ЭКГ',3000],['Процедура',6000]] },
  auto:   { e:'🔧', n:'Автосервис (СТО)', client:'Клиент', car:true, roles:{owner:'Иесі', admin:'Мастер-қабылдаушы', staff:'Шебер'},
    services:[['Диагностика',5000],['Май ауыстыру',8000],['Жүріс бөлігі',25000],['Электрика',15000],['Тежегіш',12000]] },
  tire:   { e:'🛞', n:'Шиномонтаж', client:'Клиент', car:true, roles:{owner:'Иесі', admin:'Администратор', staff:'Жұмысшы'},
    services:[['Дөңгелек ауыстыру (4)',8000],['Балансировка',4000],['Тесік жөндеу',2000],['Шина сақтау',15000]] },
  shop:   { e:'🛍️', n:'Дүкен', client:'Сатып алушы', roles:{owner:'Иесі', staff:'Сатушы'},
    services:[['Тауар сату',0]] },
  beauty: { e:'💇', n:'Сұлулық салоны', client:'Клиент', roles:{owner:'Иесі', admin:'Администратор', staff:'Шебер'},
    services:[['Шаш қию',5000],['Бояу',20000],['Маникюр',8000],['Қас-кірпік',6000]] },
  other:  { e:'💼', n:'Басқа бизнес', client:'Клиент', roles:{owner:'Иесі', admin:'Администратор', staff:'Қызметкер'},
    services:[['Қызмет',5000]] },
};
const SOURCES = ['Instagram','WhatsApp','2ГИС','TikTok','Таныс (сарафан)','Жарнама','Өзі келді','Тұрақты клиент','Басқа'];
const PAYS = [['cash','Қолма-қол'],['kaspi','Kaspi'],['card','Карта'],['debt','Қарызға']];
const EXP_CATS = ['Жалақы','Жалдау','Материал / тауар','Коммуналдық','Жарнама','Салық / төлем','Құрал-жабдық','Басқа'];
const MONTHS = ['Қаңтар','Ақпан','Наурыз','Сәуір','Мамыр','Маусым','Шілде','Тамыз','Қыркүйек','Қазан','Қараша','Желтоқсан'];
/* 2026 жылғы шамамен мөлшерлер – бухгалтермен тексеру керек, Баптауда өзгертуге болады */
const DEFAULT_SET = { rate:4, base:'income', day:10,
  fixed:[{n:'ОПЖ (10%)',a:8500},{n:'ЖЗЖ / ОПВР',a:2975},{n:'Әлеуметтік аударым (СО)',a:4250},{n:'Медсақтандыру (ВОСМС)',a:5950}] };

/* ---------------- ДЕРЕК ---------------- */
const KEY = 'qalta.v1', SKEY = 'qalta.session';
let db = load();
let me = null, view = 'home', ui = {};
function load(){ try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch(e){ return null; } }
function save(){ try { localStorage.setItem(KEY, JSON.stringify(db)); } catch(e){ toast('Сақталмады: жад толы болуы мүмкін'); } }
const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2,7);

/* ---------------- КӨМЕКШІЛЕР ---------------- */
const $ = s => document.querySelector(s);
const app = $('#app');
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = n => Math.round(n||0).toLocaleString('ru-RU').replace(/ /g,' ') + ' ₸';
const pad = n => String(n).padStart(2,'0');
const today = () => { const d=new Date(); return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`; };
const nowTime = () => { const d=new Date(); return `${pad(d.getHours())}:${pad(d.getMinutes())}`; };
const mkey = d => d.slice(0,7);
const mname = k => { const [y,m]=k.split('-'); return `${MONTHS[+m-1]} ${y}`; };
const prevMonth = k => { let [y,m]=k.split('-').map(Number); m--; if(!m){m=12;y--;} return `${y}-${pad(m)}`; };
const nextMonth = k => { let [y,m]=k.split('-').map(Number); m++; if(m>12){m=1;y++;} return `${y}-${pad(m)}`; };
const fdate = d => { const [y,m,dd]=d.split('-'); return `${dd}.${m}.${y}`; };
const normPhone = s => { let d=String(s||'').replace(/\D/g,''); if(d.length===11&&d[0]==='8') d='7'+d.slice(1); if(d.length===10) d='7'+d; return d; };
const phoneHit = (phone, q) => { if(!phone||q.length<2) return false; if(q[0]==='8') q='7'+q.slice(1); return phone.includes(q) || phone.slice(1).includes(q); };
const showPhone = d => d && d.length===11 ? `+${d[0]} ${d.slice(1,4)} ${d.slice(4,7)} ${d.slice(7,9)} ${d.slice(9)}` : (d||'');
const calc = s => { s=String(s||'').replace(/\s/g,'').replace(/,/g,'.'); if(!s) return 0; if(!/^[\d.+\-*/()]+$/.test(s)) return NaN; try { const v=Function('"use strict";return ('+s+')')(); return isFinite(v)?v:NaN; } catch(e){ return NaN; } };
const biz = () => BIZ[db.biz.type];
const roleName = r => biz().roles[r] || r;
const user = id => db.users.find(u=>u.id===id);
const client = id => db.clients.find(c=>c.id===id);
let tt; function toast(m){ const t=$('#toast'); t.textContent=m; t.classList.add('on'); clearTimeout(tt); tt=setTimeout(()=>t.classList.remove('on'),2200); }
const can = what => ({
  money:   me.role==='owner',
  report:  me.role==='owner',
  settings:me.role==='owner',
  expense: me.role!=='staff',
  allVisits: me.role!=='staff',
  delete:  me.role!=='staff',
}[what]);

async function hash(pw, salt){
  const txt = salt + '|' + pw;
  if (window.crypto && crypto.subtle) {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(txt));
    return Array.from(new Uint8Array(buf)).map(b=>b.toString(16).padStart(2,'0')).join('');
  }
  let h = 2166136261; for (let i=0;i<20000;i++){ h ^= txt.charCodeAt(i % txt.length) + i; h = Math.imul(h, 16777619); }
  return 'f' + (h>>>0).toString(16);
}

function download(name, text, type){
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], {type}));
  a.download = name; document.body.appendChild(a); a.click();
  setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}

/* ---------------- ҚАРЖЫ ЕСЕБІ ---------------- */
function monthStats(k, staffId){
  const vs = db.visits.filter(v => mkey(v.date)===k && (!staffId || v.staffId===staffId));
  const ex = staffId ? [] : db.expenses.filter(x => mkey(x.date)===k);
  const income = vs.filter(v=>v.pay!=='debt').reduce((s,v)=>s+v.amount,0);
  const debt = vs.filter(v=>v.pay==='debt').reduce((s,v)=>s+v.amount,0);
  const expense = ex.reduce((s,x)=>s+x.amount,0);
  const S = db.set;
  const taxBase = S.base==='income' ? income : Math.max(0, income-expense);
  const tax = taxBase * S.rate / 100;
  const fixed = S.fixed.reduce((s,f)=>s+(+f.a||0),0);
  const profit = income - expense - tax - fixed;
  const firstVisit = {};
  db.visits.forEach(v => { if(v.clientId && (!firstVisit[v.clientId] || v.date < firstVisit[v.clientId])) firstVisit[v.clientId]=v.date; });
  const newClients = new Set(vs.filter(v=>v.clientId && mkey(firstVisit[v.clientId])===k).map(v=>v.clientId));
  const group = (arr, key, val=x=>x.amount) => { const m={}; arr.forEach(x=>{ const g=key(x); if(!m[g]) m[g]={n:0,s:0}; m[g].n++; m[g].s+=val(x); }); return Object.entries(m).sort((a,b)=>b[1].s-a[1].s||b[1].n-a[1].n); };
  const srcOfNew = {}; newClients.forEach(id=>{ const s=client(id)?.source||'Белгісіз'; srcOfNew[s]=(srcOfNew[s]||0)+1; });
  return { vs, ex, income, debt, expense, tax, fixed, profit, newClients:newClients.size,
    bySource: Object.entries(srcOfNew).sort((a,b)=>b[1]-a[1]),
    byService: group(vs, v=>v.service),
    byStaff: group(vs, v=>user(v.staffId)?.name || '—'),
    byPay: group(vs, v=>(PAYS.find(p=>p[0]===v.pay)||[,'?'])[1]),
    byExp: group(ex, x=>x.cat) };
}

/* ---------------- КІРУ / АЛҒАШҚЫ ІСКЕ ҚОСУ ---------------- */
function render(){
  if (!db) return renderSetup();
  if (!me) { const sid = sessionGet(); me = sid && user(sid) || null; }
  if (!me) return renderLogin();
  const views = { home:renderHome, visits:renderVisits, clients:renderClients, add:renderAdd, expense:renderExpense, report:renderReport, settings:renderSettings, client:renderClient };
  app.innerHTML = (views[view] || renderHome)() + navHtml();
  window.scrollTo(0, ui.keepScroll ? window.scrollY : 0); ui.keepScroll=false;
  after();
}
function sessionGet(){ try { return localStorage.getItem(SKEY); } catch(e){ return null; } }
function sessionSet(id){ try { id ? localStorage.setItem(SKEY,id) : localStorage.removeItem(SKEY); } catch(e){} }

function renderSetup(){
  ui.setup = ui.setup || { type:'dental' };
  const t = ui.setup.type;
  app.innerHTML = `
  <div class="top"><h1>Qalta<span class="g">.</span></h1></div>
  <p class="mut">Бизнесіңе арналған дәптер: клиенттер, қабылдау, кіріс-шығыс, салық және ай сайынғы есеп.</p>
  <h2>1. Бизнес түрін таңда</h2>
  <div class="tiles">${Object.entries(BIZ).map(([k,b])=>`
    <button class="tile ${k===t?'on':''}" data-act="pick-type" data-k="${k}"><span class="e">${b.e}</span><b>${esc(b.n)}</b><span>${Object.values(b.roles).map(esc).join(' · ')}</span></button>`).join('')}
  </div>
  <form data-form="setup" class="card" style="margin-top:14px">
    <h2 style="margin-top:0">2. Бизнес аты</h2>
    <label class="f"><span>Атауы</span><input name="bname" required placeholder="Мысалы: Ақ тіс" autocomplete="organization"></label>
    <h2>3. ${esc(BIZ[t].roles.owner)} аккаунты</h2>
    <label class="f"><span>Аты-жөнің</span><input name="name" required autocomplete="name"></label>
    <div class="two">
      <label class="f"><span>Логин</span><input name="login" required autocapitalize="none" autocomplete="username"></label>
      <label class="f"><span>Пароль</span><input name="pw" type="password" required minlength="4" autocomplete="new-password"></label>
    </div>
    <button class="btn pri w">Бастау</button>
  </form>
  <button class="btn w" data-act="demo">Мысал деректермен көру (демо)</button>
  <p class="hint">Демода ойдан шығарылған клиенттер мен ақша сомалары болады. Кейін Баптаудан бәрін өшіруге болады.</p>`;
}

function renderLogin(){
  app.innerHTML = `<div class="login">
    <div style="text-align:center;margin-bottom:18px"><div style="font-size:44px">${biz().e}</div><h1>${esc(db.biz.name)}</h1><p class="mut">${esc(biz().n)} · Кіру</p></div>
    <form data-form="login" class="card">
      <label class="f"><span>Логин</span><input name="login" required autocapitalize="none" autocomplete="username"></label>
      <label class="f"><span>Пароль</span><input name="pw" type="password" required autocomplete="current-password"></label>
      <button class="btn pri w">Кіру</button>
      <p class="hint">Әр қызметкер өз логинімен кіреді. Паролін ұмытса, ${esc(biz().roles.owner)} Баптаудан жаңасын қояды.</p>
    </form>
    ${db.demo ? `<p class="hint" style="text-align:center">Демо логиндер: director / admin / doctor · пароль 1234</p>`:''}
  </div>`;
}

/* ---------------- НАВИГАЦИЯ ---------------- */
const ICON = {
  home:'<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  visits:'<rect x="3" y="4" width="18" height="17" rx="3"/><path d="M8 2v4M16 2v4M3 10h18"/>',
  clients:'<circle cx="9" cy="8" r="4"/><path d="M2 21c0-4 3-6 7-6s7 2 7 6M17 11a3 3 0 1 0 0-6M22 21c0-3-2-5-4-5.5"/>',
  expense:'<path d="M12 3v18M17 7H9.5a3 3 0 0 0 0 6h5a3 3 0 0 1 0 6H6"/>',
  report:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>'
};
function navHtml(){
  const items = [['home','Басты'],['visits','Қабылдау'],['clients',biz().client+'тер']];
  if (can('expense')) items.push(['expense','Шығыс']);
  if (can('report')) items.push(['report','Есеп']);
  if (can('settings')) items.push(['settings','Баптау']);
  const cur = view==='client' ? 'clients' : view==='add' ? 'visits' : view;
  return `<button class="fab noprint" data-act="go" data-v="add" aria-label="Жаңа қабылдау">+</button>
  <nav class="nav noprint"><div>${items.map(([k,l])=>`<button data-act="go" data-v="${k}" class="${cur===k?'on':''}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICON[k]}</svg>${esc(l)}</button>`).join('')}</div></nav>`;
}
function head(title){
  return `<div class="top"><h1 class="th">${title}</h1><div class="who"><div class="whoname"><b class="sm">${esc(me.name.split(' ')[0])}</b><div class="xs mut">${esc(roleName(me.role))}</div></div><button class="av" data-act="logout" title="Шығу">${esc(me.name.trim()[0]||'?')}</button></div></div>`;
}

/* ---------------- БАСТЫ ---------------- */
function reminderHtml(){
  if (!can('report')) return '';
  const d = new Date(), k = prevMonth(mkey(today()));
  if (d.getDate() > db.set.day + 5 || db.reports[k]) return '';
  const late = d.getDate() > db.set.day;
  return `<div class="banner"><p><b>${late?'Кешікті! ':''}${mname(k)} есебі</b><br><span class="sm">${db.set.day}-${MONTHS[d.getMonth()].toLowerCase()} күнге дейін тапсыру керек.</span></p><button class="btn s pri" data-act="open-report" data-k="${k}">Есепті ашу</button></div>`;
}
function renderHome(){
  const k = mkey(today()), td = today();
  const mine = me.role==='staff' ? me.id : null;
  const tv = db.visits.filter(v=>v.date===td && (!mine || v.staffId===mine));
  const tsum = tv.reduce((s,v)=>s+(v.pay==='debt'?0:v.amount),0);
  let h = head(esc(db.biz.name)) + reminderHtml();
  if (can('money')) {
    const s = monthStats(k);
    const tot = Math.max(s.income, 1), pc = x => Math.max(0, x/tot*100).toFixed(1);
    h += `<div class="card hl"><div class="mut sm">${mname(k)} · таза пайда</div><div class="big ${s.profit<0?'bad':''}">${money(s.profit)}</div>
      <div class="split"><i style="width:${pc(s.expense)}%;background:var(--v)"></i><i style="width:${pc(s.tax+s.fixed)}%;background:var(--o)"></i><i style="width:${pc(Math.max(0,s.profit))}%;background:var(--ok)"></i></div>
      <div class="legend"><span><i style="background:var(--v)"></i>Шығыс ${money(s.expense)}</span><span><i style="background:var(--o)"></i>Салық+төлем ${money(s.tax+s.fixed)}</span><span><i style="background:var(--ok)"></i>Пайда</span></div></div>
      <div class="kpis"><div class="kpi"><span>Айдағы кіріс</span><b>${money(s.income)}</b></div><div class="kpi"><span>Бүгін</span><b>${money(tsum)}</b></div><div class="kpi"><span>Жаңа ${esc(biz().client.toLowerCase())}</span><b>${s.newClients}</b></div>${s.debt?`<div class="kpi"><span>Қарыздар</span><b class="bad">${money(s.debt)}</b></div>`:''}</div>`;
  } else {
    const s = monthStats(k, mine);
    h += `<div class="kpis"><div class="kpi"><span>Бүгін қабылдау</span><b>${tv.length}</b></div><div class="kpi"><span>Бүгінгі касса</span><b>${money(tsum)}</b></div>${mine?`<div class="kpi"><span>${MONTHS[+k.slice(5)-1]}: менің жұмысым</span><b>${s.vs.length} рет</b></div>`:''}</div>`;
  }
  h += `<div class="row" style="margin:6px 0 4px"><button class="btn pri" data-act="go" data-v="add">+ Жаңа қабылдау</button>${can('expense')?`<button class="btn" data-act="go" data-v="expense">− Шығыс жазу</button>`:''}</div>`;
  h += `<h2>Бүгін</h2>` + visitList(tv, 'Бүгін әлі ешкім жоқ. «+» батырмасын бас.');
  return h;
}

/* ---------------- ҚАБЫЛДАУ ТІЗІМІ ---------------- */
function visitList(vs, emptyText, del){
  if (!vs.length) return `<div class="empty">${emptyText}</div>`;
  return `<div class="list">${vs.slice().sort((a,b)=>(b.date+b.time).localeCompare(a.date+a.time)).map(v=>{
    const c = client(v.clientId), st = user(v.staffId), pay = (PAYS.find(p=>p[0]===v.pay)||[,''])[1];
    return `<div class="item" ${c?`data-act="open-client" data-id="${c.id}"`:''}>
      <div><b>${esc(c?c.name:'Аты жазылмаған')}</b> <span class="mut sm">${esc(v.time||'')}</span></div>
      <div class="r ${v.pay==='debt'?'bad':''}">${money(v.amount)}</div>
      <div class="m">${esc(v.service)}${v.car?' · '+esc(v.car):''} · ${esc(st?st.name:'—')} · ${esc(pay)}${v.note?' · '+esc(v.note):''}</div>
      ${del&&can('delete')?`<div class="m"><button class="btn s dan" data-act="del-visit" data-id="${v.id}">${ui.confirm===v.id?'Иә, өшір':'Өшіру'}</button></div>`:''}
    </div>`; }).join('')}</div>`;
}
function renderVisits(){
  ui.vdate = ui.vdate || today();
  const mine = can('allVisits') ? null : me.id;
  const vs = db.visits.filter(v=>v.date===ui.vdate && (!mine || v.staffId===mine));
  const sum = vs.reduce((s,v)=>s+(v.pay==='debt'?0:v.amount),0);
  return head('Қабылдау') + `
  <div class="row"><input type="date" id="vdate" value="${ui.vdate}" max="${today()}"><button class="btn s" data-act="vtoday">Бүгін</button></div>
  <p class="mut sm">${vs.length} қабылдау · ${money(sum)}${mine?' · тек өзімнің жұмысым':''}</p>` + visitList(vs, 'Бұл күні жазба жоқ.', true);
}

/* ---------------- ЖАҢА ҚАБЫЛДАУ (басты функция) ---------------- */
function renderAdd(){
  const a = ui.add = ui.add || { q:'', clientId:null, src:'', svc:'', pay:'cash', staffId: me.role==='staff'?me.id:'' };
  const c = a.clientId && client(a.clientId);
  const staff = db.users.filter(u=>u.role!=='admin');
  if (!a.staffId) a.staffId = (staff.find(u=>u.role==='staff') || staff[0] || me).id;
  const hist = c ? db.visits.filter(v=>v.clientId===c.id) : [];
  return head('Жаңа қабылдау') + `
  <form data-form="visit" autocomplete="off">
  <div class="card">
    <label class="f"><span>Телефон немесе аты-жөні</span><input id="q" name="q" inputmode="tel" value="${esc(a.q)}" placeholder="+7 7__ ___ __ __" ${c?'readonly':''}></label>
    <div id="matches">${c ? `<div class="item found" style="cursor:default">
        <div><b>${esc(c.name)}</b> <span class="ok sm">✓ Бұрын келген</span></div><div class="r">${hist.length} рет</div>
        <div class="m">${esc(showPhone(c.phone))} · ${esc(c.source||'')} · соңғы: ${hist.length?fdate(hist.map(v=>v.date).sort().pop()):'—'}${c.note?' · '+esc(c.note):''}${c.car?' · '+esc(c.car):''}</div>
        <div class="m"><button type="button" class="btn s" data-act="unpick">Басқа адам</button></div></div>` : matchesHtml(a.q)}</div>
    ${c ? '' : `
    <label class="f"><span>Аты-жөні (жаңа ${esc(biz().client.toLowerCase())})</span><input name="cname" autocomplete="off" value="${esc(a.cname||'')}"></label>
    <span class="mut sm">Қайдан білді? Қайдан келді?</span>
    <div class="chips" style="margin:6px 0 4px">${SOURCES.map(s=>`<button type="button" class="chip ${a.src===s?'on':''}" data-act="src" data-s="${esc(s)}">${esc(s)}</button>`).join('')}</div>`}
  </div>
  <div class="card">
    <span class="mut sm">Қызмет</span>
    <div class="chips" style="margin:6px 0 10px">${db.services.map((s,i)=>`<button type="button" class="chip ${a.svc===s.n?'on':''}" data-act="svc" data-i="${i}">${esc(s.n)}</button>`).join('')}</div>
    <label class="f"><span>Не істелді (өз сөзіңмен)</span><input name="service" value="${esc(a.svc)}" placeholder="Мысалы: ${esc(db.services[0]?.n||'')}" required></label>
    ${biz().car?`<label class="f"><span>Көлік (марка, нөмір)</span><input name="car" value="${esc(a.car||(c&&c.car)||'')}" placeholder="Toyota Camry · 123 ABC 02"></label>`:''}
    <label class="f"><span>Сомасы, ₸ (есептеуге болады: 15000+2500)</span><input name="amount" id="amount" inputmode="decimal" value="${esc(a.amount||'')}" required><div class="calc" id="calcout"></div></label>
    <span class="mut sm">Төлем</span>
    <div class="chips" style="margin:6px 0 10px">${PAYS.map(([k,l])=>`<button type="button" class="chip ${a.pay===k?'on':''}" data-act="pay" data-k="${k}">${l}</button>`).join('')}</div>
    <label class="f"><span>${esc(biz().roles.staff)}</span><select name="staff" ${me.role==='staff'?'disabled':''}>
      ${staff.map(u=>`<option value="${u.id}" ${a.staffId===u.id?'selected':''}>${esc(u.name)}</option>`).join('')}</select></label>
    <div class="two"><label class="f"><span>Күні</span><input type="date" name="date" value="${a.date||today()}" max="${today()}"></label>
    <label class="f"><span>Уақыты</span><input type="time" name="time" value="${a.time||nowTime()}"></label></div>
    <label class="f"><span>Ескертпе</span><input name="note" value="${esc(a.note||'')}"></label>
  </div>
  <button class="btn pri w">Сақтау</button>
  </form>`;
}
function matchesHtml(q){
  const d = q.replace(/\D/g,''), t = q.trim().toLowerCase();
  if (d.length < 3 && t.length < 2) return '';
  const res = db.clients.filter(c => (d.length>=3 && phoneHit(c.phone,d)) || (!/\d/.test(t) && c.name.toLowerCase().includes(t))).slice(0,5);
  if (!res.length) return `<p class="hint">Табылмады. Бұл жаңа ${esc(biz().client.toLowerCase())}: төменге атын жаз.</p>`;
  return `<div class="list" style="margin-bottom:12px">${res.map(c=>{ const n=db.visits.filter(v=>v.clientId===c.id).length;
    return `<button type="button" class="item" data-act="pick-client" data-id="${c.id}"><div><b>${esc(c.name)}</b></div><div class="r ok sm">Таңдау</div><div class="m">${esc(showPhone(c.phone))} · ${n} рет келген · ${esc(c.source||'')}</div></button>`; }).join('')}</div>`;
}

/* ---------------- КЛИЕНТТЕР ---------------- */
function renderClients(){
  const q = (ui.cq||'').trim().toLowerCase(), d = q.replace(/\D/g,'');
  const stat = {}; db.visits.forEach(v=>{ if(!v.clientId) return; const s=stat[v.clientId]||(stat[v.clientId]={n:0,s:0,last:''}); s.n++; s.s+=v.amount; if(v.date>s.last) s.last=v.date; });
  let list = db.clients.filter(c => !q || (d.length>=2 && phoneHit(c.phone,d)) || c.name.toLowerCase().includes(q));
  if (me.role==='staff') { const mineIds = new Set(db.visits.filter(v=>v.staffId===me.id).map(v=>v.clientId)); list = list.filter(c=>mineIds.has(c.id)); }
  list.sort((a,b)=>(stat[b.id]?.last||'').localeCompare(stat[a.id]?.last||''));
  return head(esc(biz().client)+'тер') + `
  <input id="cq" value="${esc(ui.cq||'')}" placeholder="Телефон немесе аты бойынша іздеу" inputmode="search" style="margin-bottom:10px">
  <p class="mut sm">${list.length} адам</p>
  ${list.length ? `<div class="list">${list.slice(0,200).map(c=>{ const s=stat[c.id]||{n:0,s:0,last:''};
    return `<button class="item" data-act="open-client" data-id="${c.id}"><div><b>${esc(c.name)}</b></div><div class="r">${s.n} рет</div><div class="m">${esc(showPhone(c.phone))} · ${esc(c.source||'')}${s.last?' · соңғы '+fdate(s.last):''}${can('money')?' · '+money(s.s):''}</div></button>`; }).join('')}</div>` : `<div class="empty">Әзірге ешкім жоқ. «+» арқылы бірінші қабылдауды жаз.</div>`}`;
}
function renderClient(){
  const c = client(ui.cid); if (!c) { view='clients'; return renderClients(); }
  const vs = db.visits.filter(v=>v.clientId===c.id && (can('allVisits') || v.staffId===me.id));
  const sum = vs.reduce((s,v)=>s+v.amount,0);
  return head(esc(c.name)) + `
  <div class="card">
    <div class="row"><div><div class="mut sm">Телефон</div><b>${esc(showPhone(c.phone)||'—')}</b></div>${c.phone?`<a class="btn s" href="tel:+${esc(c.phone)}">Қоңырау</a><a class="btn s" href="https://wa.me/${esc(c.phone)}">WhatsApp</a>`:''}</div>
    <hr><div class="two"><div><div class="mut sm">Қайдан келді</div><b>${esc(c.source||'—')}</b></div><div><div class="mut sm">Келді</div><b>${vs.length} рет${can('money')?' · '+money(sum):''}</b></div></div>
  </div>
  ${can('allVisits')?`<form data-form="client" class="card"><input type="hidden" name="id" value="${c.id}">
    <label class="f"><span>Аты-жөні</span><input name="name" value="${esc(c.name)}" required></label>
    <label class="f"><span>Телефон</span><input name="phone" inputmode="tel" value="${esc(showPhone(c.phone))}"></label>
    <label class="f"><span>Қайдан келді</span><select name="source">${SOURCES.map(s=>`<option ${c.source===s?'selected':''}>${esc(s)}</option>`).join('')}</select></label>
    ${biz().car?`<label class="f"><span>Көлік</span><input name="car" value="${esc(c.car||'')}"></label>`:''}
    <label class="f"><span>Ескертпе (аллергия, ерекшелік…)</span><textarea name="note">${esc(c.note||'')}</textarea></label>
    <div class="row"><button class="btn pri">Сақтау</button><button type="button" class="btn" data-act="visit-for" data-id="${c.id}">+ Жаңа қабылдау</button></div></form>`:''}
  <h2>Тарихы</h2>${visitList(vs,'Әзірге жазба жоқ.')}`;
}

/* ---------------- ШЫҒЫС ---------------- */
function renderExpense(){
  const k = mkey(today()), ex = db.expenses.filter(x=>mkey(x.date)===k).sort((a,b)=>b.date.localeCompare(a.date));
  ui.ecat = ui.ecat || EXP_CATS[0];
  return head('Шығыс') + `
  <form data-form="expense" class="card" autocomplete="off">
    <div class="chips" style="margin-bottom:10px">${EXP_CATS.map(c=>`<button type="button" class="chip ${ui.ecat===c?'on':''}" data-act="ecat" data-c="${esc(c)}">${esc(c)}</button>`).join('')}</div>
    <label class="f"><span>Сомасы, ₸ (есептеуге болады: 3*25000)</span><input name="amount" id="amount" inputmode="decimal" required><div class="calc" id="calcout"></div></label>
    <div class="two"><label class="f"><span>Күні</span><input type="date" name="date" value="${today()}" max="${today()}"></label>
    <label class="f"><span>Не үшін</span><input name="note" placeholder="Мысалы: пломба материалы"></label></div>
    <button class="btn pri w">Шығысты сақтау</button>
  </form>
  <h2>${mname(k)}</h2>
  ${ex.length?`<div class="list">${ex.map(x=>`<div class="item"><div><b>${esc(x.cat)}</b> <span class="mut sm">${fdate(x.date)}</span></div><div class="r">${money(x.amount)}</div><div class="m">${esc(x.note||'')} · ${esc(user(x.by)?.name||'')}</div>${can('delete')?`<div class="m"><button class="btn s dan" data-act="del-exp" data-id="${x.id}">${ui.confirm===x.id?'Иә, өшір':'Өшіру'}</button></div>`:''}</div>`).join('')}</div>`:`<div class="empty">Бұл айда шығыс жоқ.</div>`}`;
}

/* ---------------- ЕСЕП ---------------- */
function bars(rows, fmt){
  if (!rows.length) return `<p class="mut sm">Дерек жоқ.</p>`;
  const max = Math.max(...rows.map(r=>r[1]), 1);
  return `<div class="bars">${rows.map(([n,v,extra])=>`<div class="bar"><span>${esc(n)}</span><div class="t"><i style="width:${(v/max*100).toFixed(1)}%"></i></div><b>${fmt(v)}${extra?` <span class="mut">${extra}</span>`:''}</b></div>`).join('')}</div>`;
}
function reportText(k, s){
  const L = [`${db.biz.name} — ${mname(k)} есебі`, ``,
    `Кіріс: ${money(s.income)}`, `Шығыс: ${money(s.expense)}`,
    `Салық (${db.set.rate}% ${db.set.base==='income'?'кірістен':'пайдадан'}): ${money(s.tax)}`,
    `Міндетті төлемдер: ${money(s.fixed)}`, `ТАЗА ПАЙДА: ${money(s.profit)}`];
  if (s.debt) L.push(`Қарызға берілген: ${money(s.debt)}`);
  L.push(``, `Қабылдау саны: ${s.vs.length}`, `Жаңа ${biz().client.toLowerCase()}: ${s.newClients}`);
  if (s.bySource.length) { L.push(``, `Жаңалар қайдан келді:`); s.bySource.forEach(([n,c])=>L.push(`  ${n}: ${c}`)); }
  if (s.byStaff.length) { L.push(``, `${biz().roles.staff} бойынша:`); s.byStaff.forEach(([n,v])=>L.push(`  ${n}: ${v.n} рет, ${money(v.s)}`)); }
  if (s.byExp.length) { L.push(``, `Шығыс түрлері:`); s.byExp.forEach(([n,v])=>L.push(`  ${n}: ${money(v.s)}`)); }
  return L.join('\n');
}
function renderReport(){
  const k = ui.rk = ui.rk || prevMonthIfEarly();
  const s = monthStats(k), done = db.reports[k];
  const totalNew = s.bySource.reduce((a,b)=>a+b[1],0) || 1;
  return head('Есеп') + `
  <div class="row noprint" style="margin-bottom:10px"><button class="btn s" data-act="rk" data-d="-1">‹</button><b style="text-align:center;flex:3">${mname(k)}</b><button class="btn s" data-act="rk" data-d="1" ${k>=mkey(today())?'disabled':''}>›</button></div>
  <div class="card hl"><div class="mut sm">Таза пайда</div><div class="big ${s.profit<0?'bad':''}">${money(s.profit)}</div>
    <p class="sm mut" style="margin:6px 0 0">${done?`<span class="ok">✓ Тапсырылды ${fdate(done.at)}</span>`:`Тапсыру мерзімі: ${db.set.day} ${MONTHS[+nextMonth(k).slice(5)-1].toLowerCase()}`}</p></div>
  <div class="kpis">
    <div class="kpi"><span>Кіріс</span><b>${money(s.income)}</b></div>
    <div class="kpi"><span>Шығыс</span><b>${money(s.expense)}</b></div>
    <div class="kpi"><span>Салық ${db.set.rate}%</span><b>${money(s.tax)}</b></div>
    <div class="kpi"><span>Міндетті төлемдер</span><b>${money(s.fixed)}</b></div>
    <div class="kpi"><span>Қабылдау</span><b>${s.vs.length}</b></div>
    <div class="kpi"><span>Жаңа ${esc(biz().client.toLowerCase())}</span><b>${s.newClients}</b></div>
    ${s.debt?`<div class="kpi"><span>Қарызға</span><b class="bad">${money(s.debt)}</b></div>`:''}
  </div>
  <div class="card"><h3>Жаңа ${esc(biz().client.toLowerCase())}тер қайдан келді</h3><p class="hint" style="margin-bottom:10px">Жарнаманың қайсысы жұмыс істеп тұрғанын осыдан көресің.</p>${bars(s.bySource, v=>`${v} адам · ${Math.round(v/totalNew*100)}%`)}</div>
  <div class="card"><h3>Қызмет бойынша</h3><br>${bars(s.byService.map(([n,v])=>[n,v.s,v.n+' рет']), money)}</div>
  <div class="card"><h3>${esc(biz().roles.staff)} бойынша</h3><br>${bars(s.byStaff.map(([n,v])=>[n,v.s,v.n+' рет']), money)}</div>
  <div class="card"><h3>Төлем түрі</h3><br>${bars(s.byPay.map(([n,v])=>[n,v.s]), money)}</div>
  <div class="card"><h3>Шығыс түрлері</h3><br>${bars(s.byExp.map(([n,v])=>[n,v.s]), money)}</div>
  <div class="noprint">
    <div class="two"><button class="btn" data-act="share-report">Мәтінмен жіберу</button><button class="btn" data-act="csv">Excel (CSV)</button></div>
    <div class="two" style="margin-top:10px"><button class="btn" data-act="print">PDF / басып шығару</button>${done?`<button class="btn" data-act="undone">Тапсырмадым</button>`:`<button class="btn pri" data-act="done">✓ Тапсырдым</button>`}</div>
    <p class="hint">Салық пен төлемдер Баптаудағы мөлшерлермен шамамен есептеледі. Ресми декларация үшін бухгалтермен тексер.</p>
  </div>`;
}
function prevMonthIfEarly(){ const t=today(); return new Date().getDate() <= db.set.day + 5 && !db.reports[prevMonth(mkey(t))] ? prevMonth(mkey(t)) : mkey(t); }

/* ---------------- БАПТАУ ---------------- */
function renderSettings(){
  const S = db.set, roles = biz().roles;
  return head('Баптау') + `
  <div class="card"><div class="row"><div style="font-size:34px;flex:none">${biz().e}</div><div><b>${esc(db.biz.name)}</b><div class="mut sm">${esc(biz().n)}</div></div></div></div>

  <h2>Қызметкерлер</h2>
  <div class="list">${db.users.map(u=>`<div class="item" style="cursor:default"><div><b>${esc(u.name)}</b> <span class="mut sm">${esc(roleName(u.role))}</span></div><div class="r mut sm">${esc(u.login)}</div>
    ${u.id!==me.id?`<div class="m row"><button class="btn s" data-act="reset-pw" data-id="${u.id}">Жаңа пароль</button><button class="btn s dan" data-act="del-user" data-id="${u.id}">${ui.confirm===u.id?'Иә, өшір':'Өшіру'}</button></div>`:''}</div>`).join('')}</div>
  <form data-form="user" class="card" style="margin-top:10px" autocomplete="off">
    <h3>+ Қызметкер қосу</h3><br>
    <label class="f"><span>Аты-жөні</span><input name="name" required></label>
    <label class="f"><span>Рөлі</span><select name="role">${Object.entries(roles).filter(([r])=>r!=='owner').concat([['owner',roles.owner]]).map(([r,n])=>`<option value="${r}">${esc(n)}</option>`).join('')}</select></label>
    <div class="two"><label class="f"><span>Логин</span><input name="login" required autocapitalize="none"></label><label class="f"><span>Пароль</span><input name="pw" required minlength="4" autocomplete="new-password"></label></div>
    <button class="btn pri w">Қосу</button>
    <p class="hint">${esc(roles.owner)}: бәрін көреді. ${roles.admin?esc(roles.admin)+': клиенттер, қабылдау, шығыс (пайданы көрмейді). ':''}${esc(roles.staff)}: тек өз жұмысын көреді.</p>
  </form>

  <h2>Қызметтер мен бағалар</h2>
  <form data-form="services" class="card">
    <textarea name="list" rows="6">${esc(db.services.map(s=>s.n+(s.p?' = '+s.p:'')).join('\n'))}</textarea>
    <p class="hint">Әр жолға бір қызмет. Бағасын «=» белгісінен кейін жаз: Пломба = 20000</p>
    <button class="btn w" style="margin-top:10px">Сақтау</button>
  </form>

  <h2>Салық және төлемдер</h2>
  <form data-form="tax" class="card">
    <div class="two"><label class="f"><span>Салық, %</span><input name="rate" inputmode="decimal" value="${S.rate}"></label>
    <label class="f"><span>Неден есептеледі</span><select name="base"><option value="income" ${S.base==='income'?'selected':''}>Кірістен</option><option value="profit" ${S.base==='profit'?'selected':''}>Пайдадан</option></select></label></div>
    <label class="f"><span>Ай сайынғы міндетті төлемдер (атауы = сомасы)</span><textarea name="fixed" rows="5">${esc(S.fixed.map(f=>f.n+' = '+f.a).join('\n'))}</textarea></label>
    <label class="f"><span>Есеп тапсыру күні (айдың)</span><input name="day" type="number" min="1" max="28" value="${S.day}"></label>
    <button class="btn w">Сақтау</button>
    <p class="hint">Әдепкі мөлшерлер шамамен алынған (ЖК, оңайлатылған декларация, 2026 ж.). Өз режиміңді бухгалтерден сұрап, осында жаз.</p>
  </form>

  <h2>Еске салғыш</h2>
  <div class="card"><p class="sm" style="margin-top:0">Телефон күнтізбесіне әр айдың ${S.day}-күніне «Есеп тапсыр» еске салғышын қос (2 күн бұрын ескертеді).</p><button class="btn w" data-act="ics">Күнтізбеге қосу</button></div>

  <h2>Сақтық көшірме</h2>
  <div class="card"><p class="sm" style="margin-top:0">Деректер тек осы телефонда сақталады. Аптасына бір рет көшірмені жүктеп, WhatsApp-қа немесе iCloud-қа сақтап қой.</p>
    <div class="two"><button class="btn" data-act="backup">Көшірме жүктеу</button><label class="btn">Көшірмеден қайтару<input type="file" id="restore" accept=".json,application/json" hidden></label></div></div>

  <h2>Телефонға орнату</h2>
  <div class="card sm"><b>iPhone:</b> Safari-де аш → «Бөлісу» (□↑) → «На экран Домой».<br><b>Android:</b> Chrome-да аш → ⋮ → «Добавить на главный экран».</div>

  <div class="row" style="margin-top:16px"><button class="btn" data-act="logout">Шығу</button><button class="btn dan" data-act="wipe">${ui.confirm==='wipe'?'Иә, БӘРІН өшір':'Барлық деректі өшіру'}</button></div>`;
}

/* ---------------- ОҚИҒАЛАР ---------------- */
function go(v){ view=v; ui.confirm=null; render(); }
function confirmTwice(id, fn){ if (ui.confirm===id){ ui.confirm=null; fn(); } else { ui.confirm=id; ui.keepScroll=true; render(); } }

app.addEventListener('click', async e => {
  const b = e.target.closest('[data-act]'); if (!b) return;
  const act = b.dataset.act, id = b.dataset.id;
  if (b.tagName==='BUTTON' && b.type!=='submit') e.preventDefault();
  const a = ui.add;
  switch (act) {
    case 'pick-type': ui.setup.type=b.dataset.k; renderSetup(); break;
    case 'demo': await makeDemo(); break;
    case 'go': if (b.dataset.v==='add') ui.add=null; go(b.dataset.v); break;
    case 'logout': me=null; sessionSet(null); view='home'; ui={}; render(); break;
    case 'open-client': ui.cid=id; go('client'); break;
    case 'visit-for': { const c=client(id); ui.add={ q:showPhone(c.phone)||c.name, clientId:c.id, pay:'cash', staffId:me.role==='staff'?me.id:'' }; go('add'); break; }
    case 'pick-client': syncAdd(); a.clientId=id; a.q=showPhone(client(id).phone)||client(id).name; ui.keepScroll=true; render(); break;
    case 'unpick': syncAdd(); a.clientId=null; a.q=''; ui.keepScroll=true; render(); setTimeout(()=>$('#q')?.focus(),0); break;
    case 'src': syncAdd(); a.src=b.dataset.s; ui.keepScroll=true; render(); break;
    case 'svc': { syncAdd(); const s=db.services[+b.dataset.i]; a.svc=s.n; if(s.p) a.amount=String(s.p); ui.keepScroll=true; render(); break; }
    case 'pay': syncAdd(); a.pay=b.dataset.k; ui.keepScroll=true; render(); break;
    case 'ecat': ui.ecat=b.dataset.c; ui.keepScroll=true; render(); break;
    case 'vtoday': ui.vdate=today(); render(); break;
    case 'del-visit': confirmTwice(id, ()=>{ db.visits=db.visits.filter(v=>v.id!==id); save(); toast('Өшірілді'); ui.keepScroll=true; render(); }); break;
    case 'del-exp': confirmTwice(id, ()=>{ db.expenses=db.expenses.filter(v=>v.id!==id); save(); toast('Өшірілді'); ui.keepScroll=true; render(); }); break;
    case 'del-user': confirmTwice(id, ()=>{ db.users=db.users.filter(u=>u.id!==id); save(); toast('Қызметкер өшірілді'); ui.keepScroll=true; render(); }); break;
    case 'reset-pw': { const u=user(id), pw=String(Math.floor(1000+Math.random()*9000)); u.salt=uid(); u.hash=await hash(pw,u.salt); save(); toast(`${u.name}: жаңа пароль ${pw}`); setTimeout(()=>toast(`${u.name}: жаңа пароль ${pw}`),2300); break; }
    case 'open-report': ui.rk=b.dataset.k; go('report'); break;
    case 'rk': ui.rk = b.dataset.d==='1' ? nextMonth(ui.rk) : prevMonth(ui.rk); render(); break;
    case 'done': db.reports[ui.rk]={at:today(), by:me.id}; save(); toast('Белгіленді ✓'); ui.keepScroll=true; render(); break;
    case 'undone': delete db.reports[ui.rk]; save(); ui.keepScroll=true; render(); break;
    case 'share-report': { const t=reportText(ui.rk, monthStats(ui.rk));
      if (navigator.share) { try { await navigator.share({title:'Есеп '+mname(ui.rk), text:t}); } catch(err){} }
      else { try { await navigator.clipboard.writeText(t); toast('Көшірілді. WhatsApp-қа қой'); } catch(err){ download(`esep-${ui.rk}.txt`, t, 'text/plain'); } } break; }
    case 'csv': csv(ui.rk); break;
    case 'print': window.print(); break;
    case 'ics': ics(); break;
    case 'backup': download(`qalta-koshirme-${today()}.json`, JSON.stringify(db), 'application/json'); toast('Көшірме жүктелді'); break;
    case 'wipe': confirmTwice('wipe', ()=>{ try{ localStorage.removeItem(KEY); }catch(err){} db=null; me=null; sessionSet(null); ui={}; view='home'; render(); }); break;
  }
});

function syncAdd(){ const f=document.querySelector('[data-form=visit]'); if(!f) return; const a=ui.add, fd=new FormData(f);
  ['q','cname','amount','note','car','date','time'].forEach(k=>{ if(fd.has(k)) a[k]=fd.get(k); }); if(fd.has('service')) a.svc=fd.get('service'); if(fd.has('staff')) a.staffId=fd.get('staff'); }

app.addEventListener('input', e => {
  const t = e.target;
  if (t.id==='q' && ui.add && !ui.add.clientId) { ui.add.q=t.value; $('#matches').innerHTML=matchesHtml(t.value); }
  if (t.id==='cq') { ui.cq=t.value; const pos=t.selectionStart; render(); const n=$('#cq'); n.focus(); n.setSelectionRange(pos,pos); }
  if (t.id==='amount') showCalc();
  if (t.id==='vdate') { ui.vdate=t.value||today(); render(); }
});
app.addEventListener('change', async e => {
  if (e.target.id!=='restore') return;
  const file = e.target.files[0]; if (!file) return;
  try { const d=JSON.parse(await file.text()); if(!d.biz||!d.users) throw 0; db=d; save(); me=null; sessionSet(null); toast('Қайтарылды. Қайта кір'); render(); }
  catch(err){ toast('Бұл файл Qalta көшірмесі емес'); }
});
function showCalc(){ const i=$('#amount'), o=$('#calcout'); if(!i||!o) return; const v=calc(i.value);
  o.textContent = !i.value ? '' : isNaN(v) ? 'Тек сан және + − × ÷' : /[+\-*/]/.test(i.value.slice(1)) ? '= '+money(v) : money(v); }
function after(){ showCalc(); }

app.addEventListener('submit', async e => {
  e.preventDefault();
  const f = e.target, fd = new FormData(f), g = k => String(fd.get(k)||'').trim();
  switch (f.dataset.form) {
    case 'setup': {
      const t = ui.setup.type, salt = uid();
      db = { v:1, biz:{type:t, name:g('bname'), created:today()}, users:[{id:uid(), name:g('name'), login:g('login').toLowerCase(), role:'owner', salt, hash:await hash(g('pw'),salt)}],
        clients:[], visits:[], expenses:[], reports:{}, set:JSON.parse(JSON.stringify(DEFAULT_SET)), services:BIZ[t].services.map(([n,p])=>({n,p})) };
      save(); me=db.users[0]; sessionSet(me.id); view='home'; toast('Дайын! Қош келдің'); render(); break; }
    case 'login': {
      const u = db.users.find(x=>x.login===g('login').toLowerCase());
      if (u && await hash(g('pw'),u.salt)===u.hash) { me=u; sessionSet(u.id); view='home'; render(); }
      else toast('Логин немесе пароль қате'); break; }
    case 'visit': {
      syncAdd(); const a = ui.add, amount = calc(a.amount);
      if (isNaN(amount) || amount<0) return toast('Соманы дұрыс жаз');
      let cid = a.clientId;
      if (!cid) {
        const phone = normPhone(a.q.replace(/[^\d+]/g,'').length>=7 ? a.q : ''), name = (a.cname||'').trim() || (!/\d/.test(a.q) ? a.q.trim() : '');
        const ex = phone && db.clients.find(c=>c.phone===phone);
        if (ex) cid = ex.id;
        else if (phone || name) { if(!a.src) return toast('Қайдан келгенін таңда'); const c={id:uid(), phone, name:name||'Аты жоқ', source:a.src, created:today()}; db.clients.push(c); cid=c.id; }
      }
      if (cid && a.car) client(cid).car = a.car;
      db.visits.push({ id:uid(), clientId:cid||null, date:a.date||today(), time:a.time||nowTime(), service:a.svc.trim(), amount, pay:a.pay, staffId:a.staffId||me.id, car:a.car||'', note:(a.note||'').trim(), by:me.id });
      save(); ui.add=null; toast('Сақталды ✓'); go('home'); break; }
    case 'client': {
      const c = client(g('id')); c.name=g('name'); c.phone=normPhone(g('phone')); c.source=g('source'); c.note=g('note'); if(fd.has('car')) c.car=g('car');
      save(); toast('Сақталды ✓'); ui.keepScroll=true; render(); break; }
    case 'expense': {
      const amount = calc(g('amount')); if (isNaN(amount)||amount<=0) return toast('Соманы дұрыс жаз');
      db.expenses.push({ id:uid(), date:g('date')||today(), cat:ui.ecat, amount, note:g('note'), by:me.id });
      save(); toast('Шығыс сақталды ✓'); render(); break; }
    case 'user': {
      const login = g('login').toLowerCase();
      if (db.users.some(u=>u.login===login)) return toast('Бұл логин бос емес');
      const salt = uid(); db.users.push({ id:uid(), name:g('name'), login, role:g('role'), salt, hash:await hash(g('pw'),salt) });
      save(); toast('Қосылды ✓'); render(); break; }
    case 'services': {
      db.services = g('list').split('\n').map(l=>l.trim()).filter(Boolean).map(l=>{ const [n,p]=l.split('='); return { n:n.trim(), p:Math.max(0,calc(p)||0) }; });
      save(); toast('Сақталды ✓'); ui.keepScroll=true; render(); break; }
    case 'tax': {
      const r = calc(g('rate')); db.set.rate = isNaN(r)?db.set.rate:r; db.set.base=g('base');
      db.set.day = Math.min(28, Math.max(1, parseInt(g('day'))||10));
      db.set.fixed = g('fixed').split('\n').map(l=>l.trim()).filter(Boolean).map(l=>{ const i=l.lastIndexOf('='); return i<0 ? {n:l,a:0} : {n:l.slice(0,i).trim(), a:calc(l.slice(i+1))||0}; });
      save(); toast('Сақталды ✓'); ui.keepScroll=true; render(); break; }
  }
});

/* ---------------- ЭКСПОРТ ---------------- */
function csv(k){
  const q = v => '"' + String(v??'').replace(/"/g,'""') + '"';
  const rows = [['Түрі','Күні','Уақыты','Клиент','Телефон','Қайдан','Қызмет','Қызметкер','Төлем','Сома']];
  db.visits.filter(v=>mkey(v.date)===k).forEach(v=>{ const c=client(v.clientId)||{}; rows.push(['Кіріс',v.date,v.time,c.name,showPhone(c.phone),c.source,v.service,user(v.staffId)?.name,(PAYS.find(p=>p[0]===v.pay)||[,''])[1],v.amount]); });
  db.expenses.filter(x=>mkey(x.date)===k).forEach(x=>rows.push(['Шығыс',x.date,'','','','',x.cat+(x.note?': '+x.note:''),user(x.by)?.name,'',-x.amount]));
  download(`esep-${k}.csv`, '﻿' + rows.map(r=>r.map(q).join(';')).join('\r\n'), 'text/csv');
}
function ics(){
  const d = new Date(), y=d.getFullYear(), m=pad(d.getMonth()+1), day=pad(db.set.day);
  const t = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Qalta//KK','BEGIN:VEVENT',`UID:qalta-report-${uid()}`,
    `DTSTAMP:${y}${m}01T000000Z`,`DTSTART:${y}${m}${day}T090000`,`DTEND:${y}${m}${day}T093000`,`RRULE:FREQ=MONTHLY;BYMONTHDAY=${db.set.day}`,
    `SUMMARY:${db.biz.name}: айлық есепті тапсыр`,'DESCRIPTION:Qalta → Есеп бөлімін аш','BEGIN:VALARM','ACTION:DISPLAY','DESCRIPTION:Есеп тапсыру','TRIGGER:-P2D','END:VALARM','END:VEVENT','END:VCALENDAR'].join('\r\n');
  download('qalta-eske-salgysh.ics', t, 'text/calendar');
}

/* ---------------- ДЕМО ---------------- */
async function makeDemo(){
  const t = ui.setup.type, B = BIZ[t];
  const mk = async (name, login, role) => { const salt=uid(); return { id:uid(), name, login, role, salt, hash:await hash('1234',salt) }; };
  const users = [await mk('Айбек Серікұлы','director','owner')];
  if (B.roles.admin) users.push(await mk('Дана Мұратқызы','admin','admin'));
  users.push(await mk('Ерлан Жақсылықов','doctor','staff'), await mk('Мадина Әлиева','doctor2','staff'));
  db = { v:1, demo:true, biz:{type:t, name:'Демо: '+B.n, created:today()}, users, clients:[], visits:[], expenses:[], reports:{},
    set:JSON.parse(JSON.stringify(DEFAULT_SET)), services:B.services.map(([n,p])=>({n,p})) };
  const names = ['Айгүл Нұрланқызы','Бауыржан Касымов','Сәуле Ахметова','Нұрсұлтан Беков','Жанар Оспанова','Арман Төлеуов','Гүлнар Сейітова','Данияр Әбілов','Әсел Қайратқызы','Тимур Ким','Мөлдір Жұмабаева','Ерасыл Нұрпейісов'];
  let seed = 7; const rnd = n => { seed = seed*16807 % 2147483647; return seed % n; };
  const srcW = ['Instagram','Instagram','Instagram','WhatsApp','2ГИС','2ГИС','Таныс (сарафан)','Таныс (сарафан)','TikTok','Өзі келді'];
  names.forEach((n,i)=>db.clients.push({ id:uid(), name:n, phone:'7701'+String(5550000+i*137).slice(0,7), source:srcW[rnd(srcW.length)], created:today(), car:B.car?['Toyota Camry','Hyundai Accent','Kia Rio','Lada Granta'][rnd(4)]:'' }));
  const staff = users.filter(u=>u.role==='staff'), now = new Date();
  for (let back=0; back<55; back++) {
    const d = new Date(now); d.setDate(d.getDate()-back); const ds = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
    const n = d.getDay()===0 ? 0 : 1 + rnd(4);
    for (let j=0;j<n;j++) { const s = B.services[rnd(B.services.length)], c = db.clients[rnd(Math.min(db.clients.length, 3 + Math.floor((55-back)/5)))];
      db.visits.push({ id:uid(), clientId:c.id, date:ds, time:`${pad(9+rnd(9))}:${pad(rnd(4)*15)}`, service:s[0], amount:s[1]||(3000+rnd(20)*1000), pay:rnd(25)===0?'debt':['cash','kaspi','kaspi','card'][rnd(4)], staffId:staff[rnd(staff.length)].id, car:c.car, note:'', by:users[0].id }); }
    if (d.getDate()===5) db.expenses.push({ id:uid(), date:ds, cat:'Жалдау', amount:250000, note:'Бөлме жалы', by:users[0].id });
    if (d.getDate()===10) db.expenses.push({ id:uid(), date:ds, cat:'Жалақы', amount:400000, note:'', by:users[0].id });
    if (back%9===3) db.expenses.push({ id:uid(), date:ds, cat:'Материал / тауар', amount:20000+rnd(10)*5000, note:'', by:users[0].id });
    if (back%14===6) db.expenses.push({ id:uid(), date:ds, cat:'Жарнама', amount:30000, note:'Instagram таргет', by:users[0].id });
  }
  save(); me = users[0]; sessionSet(me.id); view='home'; toast('Демо ашылды: логин director, пароль 1234'); render();
}

/* ---------------- ІСКЕ ҚОСУ ---------------- */
render();
if ('serviceWorker' in navigator && location.protocol === 'https:') navigator.serviceWorker.register('sw.js').catch(()=>{});
})();
