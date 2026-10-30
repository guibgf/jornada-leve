"""Gera index.html (app PWA) a partir de index.src.html (a mesma página publicada como Artifact).
Troca o armazenamento do Claude pelo Firebase e a nota por foto pela API em config.js."""
import re, pathlib
src = pathlib.Path("index.src.html").read_text(encoding="utf8")
s = src
def R(a, b, count=1):
    global s
    assert s.count(a) == count, ("trecho não encontrado", a[:80], s.count(a))
    s = s.replace(a, b)

# ---------- documento completo ----------
cut = s.index('<div class="app" id="app"></div>')
head, body = s[:cut], s[cut:]
head = head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
s = f'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#010A13">
<meta name="description" content="Jogo de hábitos para emagrecer: refeições, água, jejum e exercício viram pontos, elos e recompensas.">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icons/icon-192.png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Jornada Leve">
<style>:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}html,body{{margin:0}}[hidden]{{display:none!important}}img{{max-width:100%}}</style>
{head}</head>
<body>
{body}</body>
</html>
'''

# ---------- Firebase ----------
R('<script>\n(() => {', '''<script src="config.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore-compat.js"></script>
<script>
if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(()=>{}));
(() => {''')

R('''async function connectSample(){
  try { const s = await claude.use("sample"); if (!s) return; const lim = await s.limits().catch(()=>null);
    if (lim?.images){ sampleFn = s; S.photoOk = true; render(); } } catch {}
}''', '''let fbUser = null;
async function connectSample(){
  const url = window.APP_CONFIG?.photoApi; if (!url || !fbUser) return;
  sampleFn = { json: async (prompt, {images}) => {
    const b64 = await new Promise((ok,ko)=>{ const r=new FileReader(); r.onload=()=>ok(String(r.result).split(",")[1]); r.onerror=ko; r.readAsDataURL(images[0]); });
    const res = await fetch(url, {method:"POST", headers:{"Content-Type":"application/json", "Authorization":"Bearer "+await fbUser.getIdToken()}, body:JSON.stringify({prompt, image:b64})});
    if (res.status===429) throw {code:"rate_limited"};
    if (!res.ok) throw {code:"failed"};
    return res.json();
  }};
  S.photoOk = true; render();
}''')

start = s.index("async function connect(){")
end = s.index("function finishBoot()")
s = s[:start] + '''let rankCol = null, rankUnsub = null;
function watchLeague(){
  rankUnsub?.(); R_.rows = [];
  const lg = S.profile?.league; if (!fs || !lg) { rankCol = null; return; }
  rankCol = fs.collection("ligas/"+lg+"/jogadores");
  rankUnsub = rankCol.onSnapshot(snap => { R_.rows = snap.docs.map(d=>({id:d.id, ...d.data()})); for (const r of R_.rows) R_.names[r.id] = r.name||""; R_.ok = true; if (S.tab==="ranking") render(); },
    err => console.warn("ranking", err));
}
let fs = null;
async function connect(){
  const cfg = window.APP_CONFIG?.firebase;
  if (!cfg?.apiKey || !window.firebase) return finishBoot();
  firebase.initializeApp(cfg);
  if (!S.profile && !localStorage.getItem("jl-offline")){ S.needLogin = true; render(); }
  fs = firebase.firestore();
  try { fs.enablePersistence({synchronizeTabs:true}).catch(()=>{}); } catch {}
  const auth = firebase.auth();
  auth.getRedirectResult().catch(e=>console.warn(e));
  auth.onAuthStateChanged(u => {
    fbUser = u;
    if (!u){ S.needLogin = !localStorage.getItem("jl-offline"); finishBoot(); return; }
    S.needLogin = false; myId = u.uid; rankDb = true;
    connectSample();
    col = fs.collection("usuarios/"+u.uid+"/dados");
    let first = true;
    col.onSnapshot(snap => {
      if (snap.metadata?.hasPendingWrites) return;
      const days = {}; let profile = null;
      snap.docs.forEach(doc => {
        if (doc.id==="profile") profile = doc.data();
        else if (doc.id.startsWith("day-")) days[doc.id.slice(4)] = doc.data();
      });
      if (first && !profile && S.profile){
        writeDoc("profile", S.profile);
        Object.entries(S.days).forEach(([d,v])=>writeDoc("day-"+d, v));
      } else {
        S.profile = profile ? structuredClone(profile) : S.profile;
        for (const [d,v] of Object.entries(days)) S.days[d] = structuredClone(v);
      }
      if (first){ const lg = new URLSearchParams(location.search).get("liga"); if (lg && S.profile && S.profile.league!==lg){ S.profile.league = lg.slice(0,24); saveProfile(); toast("Você entrou na liga "+lg); history.replaceState(null,"",location.pathname); } }
      if (first || S.profile?.league !== rankCol?.path?.split("/")[1]) watchLeague();
      first = false; S.cloud = true; cache(); finishBoot();
    }, err => { console.warn(err); finishBoot(); });
  });
}
function loginView(){
  const frag = $(`<div class="stack setup" style="padding-top:12vh;text-align:center">
    <div style="width:120px;height:132px;margin:0 auto">${emblem(1)}</div>
    <div><span class="eyebrow">Jornada Leve</span><h2 class="hero-title">Cada refeição no plano vale pontos</h2>
    <p class="lead">Entre com sua conta Google para salvar seu progresso na nuvem e disputar o ranking com os amigos.</p></div>
    <button class="btn block" id="glogin" style="padding:15px">Entrar com Google</button>
    <button class="btn ghost block" id="offline">Usar só neste aparelho</button></div>`);
  frag.getElementById("glogin").onclick = async () => { const auth = firebase.auth(), prov = new firebase.auth.GoogleAuthProvider();
    try { await auth.signInWithPopup(prov); } catch(e){ if (["auth/popup-blocked","auth/operation-not-supported-in-this-environment","auth/cancelled-popup-request"].includes(e.code)) auth.signInWithRedirect(prov); else toast("Não deu para entrar. Tente de novo."); } };
  frag.getElementById("offline").onclick = () => { try{localStorage.setItem("jl-offline","1");}catch{} S.needLogin=false; render(); };
  return frag;
}
''' + s[end:]

# login gate in render
R('''  if (!S.profile){ tabs.hidden = true; app.replaceChildren(setupView()); return; }''',
  '''  if (S.needLogin){ tabs.hidden = true; app.replaceChildren(loginView()); return; }
  if (!S.profile){ tabs.hidden = true; app.replaceChildren(setupView()); return; }''')
R('''S.cloud ? "Salvo na sua conta, aparece em qualquer aparelho."''', '''S.cloud ? `Salvo na sua conta Google${fbUser?.email?` (${esc(fbUser.email)})`:""}.`''')

# ranking: per-league collection, name stored in the doc
R('''    if (!rankDb || !myId || !S.profile?.ranking?.on) return;''', '''    if (!rankCol || !myId || !S.profile?.ranking?.on) return;''')
R('''const doc = {level:s.level,''', '''const doc = {name:(fbUser?.displayName||"Jogador").split(" ").slice(0,2).join(" "), level:s.level,''')
R('''    try { await rankDb.doc("ranking/"+myId).set(doc); }''', '''    try { await rankCol.doc(myId).set(doc); }''')
R('''    else if (rankDb && myId){ try { await rankDb.doc("ranking/"+myId).delete(); lastRank=""; } catch {} toast("Você saiu do ranking"); }''',
  '''    else if (rankCol && myId){ try { await rankCol.doc(myId).delete(); lastRank=""; } catch {} toast("Você saiu do ranking"); }''')
R('''  if (!rankDb) lb.append($(`<p class="note">O ranking funciona quando o jogo está salvo na sua conta.</p>`));''',
  '''  if (!fbUser) lb.append($(`<p class="note">Entre com a conta Google (em Ajustes) para usar o ranking.</p>`));
  else if (!S.profile.league) lb.append($(`<p class="note">Crie ou entre numa liga abaixo para ver o ranking.</p>`));''')
i = s.index('    <section class="card"><div class="card-head"><h2>Chamar amigos</h2></div>')
j = s.index('</section>', i) + len('</section>')
s = s[:i] + '''    <section class="card stack"><div class="card-head" style="margin:0"><h2>Sua liga</h2>${S.profile.league?`<span class="eyebrow">${esc(S.profile.league)}</span>`:""}</div>
      <p class="note" style="margin:0">A liga é o grupo que aparece no seu ranking. Só quem tem o código vê.</p>
      <form id="lform" style="display:flex;gap:8px"><input type="text" id="lcode" maxlength="24" placeholder="Código da liga" aria-label="Código da liga" value="${esc(S.profile.league||"")}"><button class="btn" style="padding:8px 14px">Entrar</button></form>
      <button class="btn ghost block" type="button" id="lnew">Criar liga nova</button>
      ${S.profile.league?`<button class="btn block" type="button" id="linvite">Copiar convite para amigos</button>`:""}
      <p class="note" style="margin:0">O amigo abre o convite, instala o app, entra com o Google e liga "Aparecer no ranking".</p></section>''' + s[j:]
R('''  frag.querySelectorAll("#rmode button")''', '''  const setLeague = code => { code = code.trim().toUpperCase().replace(/[^A-Z0-9-]/g,"").slice(0,24); if (!code) return toast("Digite um código");
    if (rankCol && myId && S.profile.ranking?.on) rankCol.doc(myId).delete().catch(()=>{});
    S.profile.league = code; saveProfile(); lastRank=""; watchLeague(); syncRank(); toast("Liga "+code); render(); };
  frag.getElementById("lform").onsubmit = e => { e.preventDefault(); setLeague(document.getElementById("lcode").value); };
  frag.getElementById("lnew").onclick = () => setLeague("LIGA-"+Math.random().toString(36).slice(2,7).toUpperCase());
  frag.getElementById("linvite")?.addEventListener("click", async () => {
    const link = location.origin+location.pathname+"?liga="+encodeURIComponent(S.profile.league);
    const text = `Bora competir no Jornada Leve! Instala o app e entra na minha liga: ${link}`;
    try { if (navigator.share) await navigator.share({title:"Jornada Leve", text}); else { await navigator.clipboard.writeText(text); toast("Convite copiado"); } } catch {} });
  frag.querySelectorAll("#rmode button")''')
R('''<span class="note">Opcional. O peso em si nunca aparece.</span>''', '''<span class="note">Opcional. O peso em si nunca aparece. Seu nome do Google aparece para a liga.</span>''')

# ajustes: conta
R('''    ${editing?`<p class="note">Seus dados ficam salvos na sua conta do Claude. Mudar os hábitos recalcula os pontos dos dias anteriores.</p>`:""}''',
  '''    ${editing?`<p class="note">Mudar os hábitos recalcula os pontos dos dias anteriores.</p>
      ${window.firebase&&window.APP_CONFIG?.firebase?.apiKey?(fbUser?`<button class="btn ghost block" type="button" id="logout">Sair da conta ${esc(fbUser.email||"")}</button>`:`<button class="btn ghost block" type="button" id="login2">Entrar com Google para salvar na nuvem</button>`):""}`:""}''')
R('''  return frag;
}

document.getElementById("tabs")''', '''  frag.getElementById("logout")?.addEventListener("click", () => firebase.auth().signOut().then(()=>{ try{localStorage.removeItem("jl-offline")}catch{} location.reload(); }));
  frag.getElementById("login2")?.addEventListener("click", () => { try{localStorage.removeItem("jl-offline")}catch{} S.needLogin=true; render(); });
  return frag;
}

document.getElementById("tabs")''')
s = s.replace("Salvo só neste aparelho.", "Salvo só neste aparelho. Entre com o Google em Ajustes para salvar na nuvem.")
assert "claude.use" not in s and "window.claude" not in s.replace("window.claude?.hot","")
pathlib.Path("index.html").write_text(s, encoding="utf8")
print("index.html gerado", len(s))
