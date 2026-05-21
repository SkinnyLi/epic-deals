"""
Epic & Steam 优惠查看器 - 纯前端版
浏览器直接请求API，服务器只提供网页
使用方法: python app.py
"""

from flask import Flask
import os

app = Flask(__name__)

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Epic & Steam 优惠查看</title>
<style>
:root{--bg:#0a0a0f;--bg2:#12121a;--card:#1a1a2e;--t1:#e8e8f0;--t2:#8888a8;--blue:#0078f2;--green:#00d26a;--orange:#ff6b35;--purple:#7c3aed;--border:#2a2a40;--r:12px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif;background:var(--bg);color:var(--t1);min-height:100vh}
.header{background:linear-gradient(135deg,#0d0d1a,#1a1a35);border-bottom:1px solid var(--border);padding:1rem;position:sticky;top:0;z-index:100}
.header-inner{max-width:1400px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem}
.logo{display:flex;align-items:center;gap:.6rem}
.logo-icon{font-size:1.8rem}
.logo h1{font-size:1.2rem;font-weight:700;background:linear-gradient(135deg,var(--blue),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.btn{padding:.45rem .8rem;border:1px solid var(--border);border-radius:8px;background:var(--card);color:var(--t1);cursor:pointer;font-size:.85rem}
.btn:hover{border-color:var(--blue)}
.tabs{max-width:1400px;margin:1rem auto 0;padding:0 1rem;display:flex;gap:.3rem;flex-wrap:wrap}
.tab{padding:.55rem 1rem;border:1px solid var(--border);border-radius:8px 8px 0 0;background:transparent;color:var(--t2);cursor:pointer;font-size:.85rem;border-bottom:none}
.tab.epic{--c:var(--blue)}.tab.steam{--c:var(--purple)}
.tab.active{color:var(--t1);background:var(--bg2);border-color:var(--c)}
.tab b{font-weight:600}.tab span{padding:.1rem .4rem;border-radius:8px;font-size:.7rem;margin-left:.3rem}
.tab.epic span{background:rgba(0,120,242,.2);color:var(--blue)}
.tab.steam span{background:rgba(124,58,237,.2);color:var(--purple)}
.main{max-width:1400px;margin:0 auto;padding:0 1rem 1.5rem}
.tc{display:none;background:var(--bg2);border:1px solid var(--border);border-radius:0 var(--r) var(--r) var(--r);padding:1.5rem}
.tc.active{display:block}
.sh{margin-bottom:1.2rem}
.sh h2{font-size:1.3rem}
.sh h2 em{font-style:normal;font-size:.85rem;padding:.2rem .6rem;border-radius:12px;margin-right:.5rem}
.sh h2 em.epic{background:rgba(0,120,242,.2);color:var(--blue)}
.sh h2 em.steam{background:rgba(124,58,237,.2);color:var(--purple)}
.grid{display:grid;gap:1rem;grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.gc{background:var(--card);border-radius:var(--r);overflow:hidden;border:1px solid var(--border);transition:.3s}
.gc:hover{transform:translateY(-3px);border-color:var(--blue);box-shadow:0 4px 20px rgba(0,0,0,.4)}
.gc img{width:100%;aspect-ratio:16/7;object-fit:cover;background:var(--bg);display:block}
.gc-body{padding:.8rem}
.gc-title{font-size:.95rem;font-weight:600;margin-bottom:.3rem}
.gc-desc{font-size:.75rem;color:var(--t2);margin-bottom:.6rem;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.gc-foot{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.4rem}
.tag{padding:.2rem .6rem;border-radius:16px;font-size:.75rem;font-weight:700;color:#fff}
.tag-free{background:linear-gradient(135deg,var(--green),#00b85e)}
.tag-disc{background:linear-gradient(135deg,var(--blue),#0055cc)}
.pw{display:flex;flex-direction:column;align-items:flex-end}
.po{font-size:.7rem;color:var(--t2);text-decoration:line-through}
.pn{color:var(--green);font-weight:700;font-size:.9rem}
.pc{font-size:.65rem;color:var(--t2)}
.ld{grid-column:1/-1;text-align:center;padding:3rem;color:var(--t2)}
.spinner{display:inline-block;width:30px;height:30px;border:3px solid var(--border);border-top-color:var(--blue);border-radius:50%;animation:sp .8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.empty{grid-column:1/-1;text-align:center;padding:3rem;color:var(--t2)}
.empty .icon{font-size:2.5rem;margin-bottom:.8rem}
.err-msg{font-size:.8rem;margin-top:.5rem;word-break:break-all}
@media(max-width:768px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<header class="header"><div class="header-inner">
<div class="logo"><span class="logo-icon">🎮</span><h1>Epic & Steam 优惠查看</h1></div>
<div><button class="btn" onclick="loadAll()">🔄 刷新</button></div>
</div></header>
<nav class="tabs">
<button class="tab epic active" onclick="sw('ef',this)"><b>🎁 Epic</b><span>免费</span></button>
<button class="tab epic" onclick="sw('ed',this)"><b>💰 Epic</b><span>折扣</span></button>
<button class="tab steam" onclick="sw('sf',this)"><b>🎮 Steam</b><span>免费</span></button>
<button class="tab steam" onclick="sw('sd',this)"><b>💰 Steam</b><span>折扣</span></button>
</nav>
<main class="main">
<div id="t-ef" class="tc active"><div class="sh"><h2><em class="epic">Epic</em>🎁 当前免费游戏</h2></div><div id="ef" class="grid"><div class="ld"><div class="spinner"></div><br>加载中...</div></div></div>
<div id="t-ed" class="tc"><div class="sh"><h2><em class="epic">Epic</em>💰 折扣游戏</h2></div><div id="ed" class="grid"><div class="ld"><div class="spinner"></div><br>加载中...</div></div></div>
<div id="t-sf" class="tc"><div class="sh"><h2><em class="steam">Steam</em>🎮 当前免费游戏</h2></div><div id="sf" class="grid"><div class="ld"><div class="spinner"></div><br>加载中...</div></div></div>
<div id="t-sd" class="tc"><div class="sh"><h2><em class="steam">Steam</em>💰 折扣游戏</h2></div><div id="sd" class="grid"><div class="ld"><div class="spinner"></div><br>加载中...</div></div></div>
</main>
<script>
var R=7.25;
function $(i){return document.getElementById(i)}
function sw(n,el){document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active')});document.querySelectorAll('.tc').forEach(function(t){t.classList.remove('active')});el.classList.add('active');$('t-'+n).classList.add('active')}
function c2c(c,cur){if(!c)return'';var n=cur==='CNY'?c/100:c/100*R;return n===0?'':'约¥'+Math.round(n)}
function c2u(c){if(!c)return'';var n=c/100;return n===0?'':'$'+n.toFixed(2)}
function fd(s){if(!s)return'';try{return new Date(s).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}catch(e){return s.substring(0,16)}}
function card(g,t){var c=document.createElement('a');c.className='gc';c.href=g.url;c.target='_blank';c.style.cssText='text-decoration:none;color:inherit';var tg=t==='free'?'<span class="tag tag-free">免费</span>':'<span class="tag tag-disc">-'+g.discount+'%</span>';var pr=t==='free'?'<div class="pw"><span class="pn">免费</span></div>':'<div class="pw">'+(g.originalPrice?'<span class="po">'+g.originalPrice+'</span>':'')+'<span class="pn">'+g.discountPrice+'</span>'+(g.discountPriceCNY?'<span class="pc">'+g.discountPriceCNY+'</span>':'')+'</div>';c.innerHTML='<img src="'+g.image+'" onerror="this.style.display=\'none\'"><div class="gc-body"><div class="gc-title">'+g.title+'</div>'+(g.description?'<div class="gc-desc">'+g.description+'</div>':'')+'<div class="gc-foot">'+tg+pr+'</div></div>';return c}
function show(el,list,type){if(!list.length){el.innerHTML='<div class="empty"><div class="icon">🔍</div><p>暂无数据</p></div>';return}el.innerHTML='';list.forEach(function(g){el.appendChild(card(g,type))})}
function err(el,msg){el.innerHTML='<div class="empty"><div class="icon">⚠️</div><p>加载失败</p><p class="err-msg">'+msg+'</p><p style="margin-top:.5rem;font-size:.75rem">请点击刷新重试</p></div>'}

function loadEpic(){
['ef','ed'].forEach(function(id){$(id).innerHTML='<div class="ld"><div class="spinner"></div><br>加载中...</div>'});
var url='https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=zh-CN&country=US&allowCountries=US';
fetch(url).then(function(r){return r.json()}).then(function(data){
var els=data.data.Catalog.searchStore.elements;
var free=[],disc=[];
els.forEach(function(g){
var p=g.promotions||{};var offers=p.promotionalOffers||[];
if(!offers.length)return;
var pr=g.price||{};var tp=pr.totalPrice||{};var fp=tp.fmtPrice||{};
var orig=fp.originalPrice||'';var disc=fp.discountPrice||'';
var info={id:g.id,title:g.title||'未知',description:(g.description||'').trim().substring(0,150),url:'https://store.epicgames.com/zh-CN/p/'+(g.productSlug||g.urlSlug||g.id)};
for(var t of['DieselStoreFrontWide','OfferImageWide','Thumbnail']){for(var im of(g.keyImages||[])){if(im.type===t){info.image=im.url;break}}if(info.image)break}
if(!info.image)info.image='';
offers.forEach(function(os){(os.promotionalOffers||[]).forEach(function(o){
var dp=o.discountSetting||{};var pct=dp.discountPercentage;
info.startDate=fd(o.startDate);info.endDate=fd(o.endDate);
info.discount=pct>=0?100-pct:0;
info.originalPrice=orig;info.discountPrice=disc;
if(pct===0){free.push(info)}
else if(pct>0){disc.push(info)}
})});
});
disc.sort(function(a,b){return b.discount-a.discount});
show($('ef'),free,'free');show($('ed'),disc,'deal');
}).catch(function(e){err($('ef'),e.message);err($('ed'),e.message)});
}

function loadSteam(){
['sf','sd'].forEach(function(id){$(id).innerHTML='<div class="ld"><div class="spinner"></div><br>加载中...</div>'});
var url='https://store.steampowered.com/api/featuredcategories?cc=cn&l=schinese';
fetch(url).then(function(r){return r.json()}).then(function(data){
var free=[],disc=[],seen={};
for(var cat in data){var items=(data[cat]||{}).items||[];
items.forEach(function(g){if(seen[g.id])return;seen[g.id]=1;
var fp=g.final_price||0,op=g.original_price||0,cur=g.currency||'CNY';
var info={id:g.id,title:g.name||'未知',description:'',url:'https://store.steampowered.com/app/'+g.id,image:g.header_image||g.small_capsule_image||''};
if(fp===0||g.is_free){
info.originalPrice=c2u(op);info.discountPrice='免费';info.originalPriceCNY=c2c(op,cur);info.discountPriceCNY='';
free.push(info);
}else if(g.discounted&&g.discount_percent>0){
info.originalPrice=c2u(op);info.discountPrice=c2u(fp);info.originalPriceCNY=c2c(op,cur);info.discountPriceCNY=c2c(fp,cur);info.discount=g.discount_percent;
disc.push(info);
}});
}
disc.sort(function(a,b){return b.discount-a.discount});
show($('sf'),free,'free');show($('sd'),disc,'deal');
}).catch(function(e){err($('sf'),e.message);err($('sd'),e.message)});
}

function loadAll(){loadEpic();loadSteam()}
loadAll();
</script>
</body></html>"""

@app.route("/")
def index():
    return HTML

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
