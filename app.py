"""
Epic Games 折扣 & 免费游戏查看器 - 增强版 v2
新功能：人民币价格显示
使用方法: python app.py
访问: http://localhost:5000
"""

import requests as req
from flask import Flask, jsonify, request
from datetime import datetime
import json, os, re

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTIFY_FILE = os.path.join(BASE_DIR, "notified_games.json")

EPIC_APIS = [
    "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions",
    "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions",
]
USD_TO_CNY = 7.25

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

def load_json(path, default=None):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return default if default is not None else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def usd_to_cny(usd_str):
    if not usd_str:
        return ""
    try:
        num = float(re.sub(r'[^0-9.]', '', usd_str))
        if num == 0:
            return ""
        return f"\u7ea6\u00a5{num * USD_TO_CNY:.0f}"
    except:
        return ""

def get_image(game):
    for t in ["DieselStoreFrontWide", "OfferImageWide", "Thumbnail"]:
        for img in game.get("keyImages", []):
            if img.get("type") == t:
                return img["url"]
    return ""

def fmt_date(s):
    if not s:
        return ""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except:
        return s[:16]

def get_url(game):
    slug = game.get("productSlug") or game.get("urlSlug") or ""
    return f"https://store.epicgames.com/zh-CN/p/{slug}" if slug else f"https://store.epicgames.com/zh-CN/p/{game.get('id', '')}"

def fetch_epic_api(locale, country):
    """尝试多个 API 端点"""
    last_err = None
    for api_url in EPIC_APIS:
        try:
            r = req.get(api_url, params={
                "locale": locale, "country": country, "allowCountries": country
            }, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                data = r.json()
                elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
                if elements:
                    return data
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
    raise Exception(f"所有API端点均失败: {last_err}")

def fetch_data(locale="zh-CN", country="CN"):
    try:
        data = fetch_epic_api(locale, country)
    except Exception as e:
        return {"error": str(e), "free": [], "discounts": []}
    
    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
    free_games, discounts = [], []
    
    for g in elements:
        promo = g.get("promotions") or {}
        offers = promo.get("promotionalOffers", [])
        if not offers:
            continue
        
        price_data = g.get("price", {}).get("totalPrice", {})
        fmt = price_data.get("fmtPrice", {})
        orig = fmt.get("originalPrice", "")
        disc = fmt.get("discountPrice", "")
        
        info = {
            "id": g.get("id", ""),
            "title": g.get("title", "\u672a\u77e5\u6e38\u620f"),
            "description": g.get("description", "").strip()[:150],
            "image": get_image(g),
            "url": get_url(g),
            "originalPrice": orig,
            "discountPrice": disc,
            "originalPriceCNY": usd_to_cny(orig),
            "discountPriceCNY": usd_to_cny(disc),
            "seller": g.get("seller", {}).get("name", "")
        }
        
        for offer_set in offers:
            offer_list = offer_set.get("promotionalOffers", [])
            if offer_list:
                o = offer_list[0]
                start, end = o.get("startDate", ""), o.get("endDate", "")
                discount_pct = o.get("discountSetting", {}).get("discountPercentage", -1)
                info["startDate"] = fmt_date(start)
                info["endDate"] = fmt_date(end)
                info["discount"] = 100 - discount_pct if discount_pct >= 0 else 0
                
                if discount_pct == 0:
                    free_games.append(info)
                elif discount_pct > 0:
                    discounts.append(info)
                break
    
    discounts.sort(key=lambda x: x.get("discount", 0), reverse=True)
    return {"free": free_games, "discounts": discounts}

@app.route("/")
def index():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Epic Games \u4f18\u60e0\u67e5\u770b\u5668</title>
<style>
:root{--bg:#0a0a0f;--bg2:#12121a;--card:#1a1a2e;--t1:#e8e8f0;--t2:#8888a8;--blue:#0078f2;--green:#00d26a;--orange:#ff6b35;--border:#2a2a40;--r:12px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif;background:var(--bg);color:var(--t1);min-height:100vh}
.header{background:linear-gradient(135deg,#0d0d1a,#1a1a35);border-bottom:1px solid var(--border);padding:1rem;position:sticky;top:0;z-index:100}
.header-inner{max-width:1400px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem}
.logo{display:flex;align-items:center;gap:.6rem}
.logo h1{font-size:1.2rem;font-weight:700;background:linear-gradient(135deg,var(--blue),#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.btn{padding:.45rem .8rem;border:1px solid var(--border);border-radius:8px;background:var(--card);color:var(--t1);cursor:pointer;font-size:.85rem}
.btn:hover{border-color:var(--blue)}
.tabs{max-width:1400px;margin:1rem auto 0;padding:0 1rem;display:flex;gap:.4rem}
.tab{padding:.6rem 1.2rem;border:1px solid var(--border);border-radius:8px 8px 0 0;background:transparent;color:var(--t2);cursor:pointer;font-size:.9rem;border-bottom:none}
.tab.active{color:var(--t1);background:var(--bg2);border-color:var(--blue)}
.main{max-width:1400px;margin:0 auto;padding:0 1rem 1.5rem}
.tab-content{display:none;background:var(--bg2);border:1px solid var(--border);border-radius:0 var(--r) var(--r) var(--r);padding:1.5rem}
.tab-content.active{display:block}
.sh{margin-bottom:1.2rem}
.sh h2{font-size:1.3rem}
.grid{display:grid;gap:1rem}
.free-grid{grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.discount-grid{grid-template-columns:repeat(auto-fill,minmax(280px,1fr))}
.gc{background:var(--card);border-radius:var(--r);overflow:hidden;border:1px solid var(--border);transition:.3s}
.gc:hover{transform:translateY(-3px);border-color:var(--blue)}
.gc img{width:100%;aspect-ratio:16/7;object-fit:cover;background:var(--bg)}
.gc-body{padding:.8rem}
.gc-title{font-size:.95rem;font-weight:600;margin-bottom:.3rem}
.gc-desc{font-size:.75rem;color:var(--t2);margin-bottom:.6rem}
.gc-foot{display:flex;justify-content:space-between;align-items:center}
.tag{padding:.2rem .6rem;border-radius:16px;font-size:.75rem;font-weight:700;color:#fff}
.tag-free{background:linear-gradient(135deg,var(--green),#00b85e)}
.tag-disc{background:linear-gradient(135deg,var(--blue),#0055cc)}
.price-new{color:var(--green);font-weight:700}
.price-cny{font-size:.75rem;color:var(--t2);margin-left:.3rem}
.loading{grid-column:1/-1;text-align:center;padding:3rem;color:var(--t2)}
.empty{grid-column:1/-1;text-align:center;padding:3rem;color:var(--t2)}
.empty .icon{font-size:2.5rem;margin-bottom:.8rem}
@media(max-width:768px){.free-grid,.discount-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<header class="header"><div class="header-inner">
<div class="logo"><span>\U0001f3ae</span><h1>Epic Games \u4f18\u60e0\u67e5\u770b\u5668</h1></div>
<div><button class="btn" onclick="loadData()">\U0001f504 \u5237\u65b0</button></div>
</div></header>
<nav class="tabs">
<button class="tab active" onclick="switchTab('free',this)">\U0001f381 \u514d\u8d39\u6e38\u620f</button>
<button class="tab" onclick="switchTab('disc',this)">\U0001f4b0 \u6298\u6263\u6e38\u620f</button>
</nav>
<main class="main">
<div id="tab-free" class="tab-content active">
<div class="sh"><h2>\U0001f381 \u5f53\u524d\u514d\u8d39\u6e38\u620f</h2></div>
<div id="free-list" class="grid free-grid"><div class="loading">\u52a0\u8f7d\u4e2d...</div></div>
</div>
<div id="tab-disc" class="tab-content">
<div class="sh"><h2>\U0001f4b0 \u6298\u6263\u6e38\u620f</h2></div>
<div id="disc-list" class="grid discount-grid"><div class="loading">\u52a0\u8f7d\u4e2d...</div></div>
</div>
</main>
<script>
function $(id){return document.getElementById(id)}
function switchTab(name,el){
document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active')});
document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active')});
el.classList.add('active');
$('tab-'+name).classList.add('active');
}
function card(g,type){
var c=document.createElement('a');c.className='gc';c.href=g.url;c.target='_blank';c.style.cssText='text-decoration:none;color:inherit';
var tag=type==='free'?'<span class="tag tag-free">\u514d\u8d39</span>':'<span class="tag tag-disc">-'+g.discount+'%</span>';
var price=type==='free'?'<span class="price-new">\u514d\u8d39</span>':'<span class="price-new">'+g.discountPrice+'</span><span class="price-cny">'+g.discountPriceCNY+'</span>';
c.innerHTML='<img src="'+g.image+'" onerror="this.style.display=\\'none\\'"><div class="gc-body"><div class="gc-title">'+g.title+'</div><div class="gc-desc">'+g.description+'</div><div class="gc-foot">'+tag+'<div>'+price+'</div></div></div>';
return c;
}
function loadData(){
var fl=$('free-list'),dl=$('disc-list');
fl.innerHTML='<div class="loading">\u52a0\u8f7d\u4e2d...</div>';
dl.innerHTML='<div class="loading">\u52a0\u8f7d\u4e2d...</div>';
fetch('/api/games').then(function(r){return r.json()}).then(function(d){
fl.innerHTML='';dl.innerHTML='';
if(d.error){
fl.innerHTML='<div class="empty"><div class="icon">\u26a0\ufe0f</div><p>\u52a0\u8f7d\u5931\u8d25: '+d.error+'</p><p style="margin-top:.5rem;font-size:.8rem">\u8bf7\u7a0d\u540e\u70b9\u51fb\u5237\u65b0\u91cd\u8bd5</p></div>';
return;
}
if(d.free.length===0){fl.innerHTML='<div class="empty"><div class="icon">\U0001f4ed</div><p>\u6682\u65e0\u514d\u8d39\u6e38\u620f</p></div>';}
else{d.free.forEach(function(g){fl.appendChild(card(g,'free'))});}
if(d.discounts.length===0){dl.innerHTML='<div class="empty"><div class="icon">\U0001f50d</div><p>\u6682\u65e0\u6298\u6263\u6e38\u620f</p></div>';}
else{d.discounts.forEach(function(g){dl.appendChild(card(g,'disc'))});}
}).catch(function(err){
fl.innerHTML='<div class="empty"><div class="icon">\u274c</div><p>\u7f51\u7edc\u9519\u8bef</p></div>';
dl.innerHTML='<div class="empty"><div class="icon">\u274c</div><p>\u7f51\u7edc\u9519\u8bef</p></div>';
});
}
loadData();
</script>
</body></html>"""

@app.route("/api/games")
def api_games():
    return jsonify(fetch_data())

@app.route("/api/notifications", methods=["POST"])
def api_notify():
    data = request.get_json(force=True)
    notified = load_json(NOTIFY_FILE, {"ids": []})
    if data.get("action") == "check":
        games = fetch_data()
        new_ids = [g["id"] for g in games["free"] if g["id"] not in notified["ids"]]
        for gid in new_ids:
            notified["ids"].append(gid)
        save_json(NOTIFY_FILE, notified)
        return jsonify({"new_count": len(new_ids)})
    return jsonify({"error": "unknown"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
