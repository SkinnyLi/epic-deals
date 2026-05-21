"""
Epic Games & Steam 优惠查看器 - 增强版
功能：Epic/Steam 免费游戏 + 折扣 + 人民币价格
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

# Epic API
EPIC_APIS = [
    "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions",
    "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions",
]
# Steam API
STEAM_API = "https://store.steampowered.com/api/featuredcategories"

USD_TO_CNY = 7.25

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# ═══════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════

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

def cents_to_cny(cents, currency="USD"):
    """美分/整数价格转人民币"""
    try:
        if currency == "CNY":
            num = float(cents) / 100
        else:
            num = float(cents) / 100 * USD_TO_CNY
        if num == 0:
            return ""
        return f"\u7ea6\u00a5{num:.0f}"
    except:
        return ""

def cents_to_usd(cents):
    """美分转美元"""
    try:
        num = float(cents) / 100
        if num == 0:
            return ""
        return f"${num:.2f}"
    except:
        return ""

# ═══════════════════════════════════════════
#  Epic 数据获取
# ═══════════════════════════════════════════

def fetch_epic_api(locale, country):
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
    raise Exception(f"Epic API\u5747\u5931\u8d25: {last_err}")

def get_epic_image(game):
    for t in ["DieselStoreFrontWide", "OfferImageWide", "Thumbnail"]:
        for img in game.get("keyImages", []):
            if img.get("type") == t:
                return img["url"]
    return ""

def get_epic_url(game):
    slug = game.get("productSlug") or game.get("urlSlug") or ""
    return f"https://store.epicgames.com/zh-CN/p/{slug}" if slug else f"https://store.epicgames.com/zh-CN/p/{game.get('id', '')}"

def fmt_date(s):
    if not s:
        return ""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except:
        return s[:16]

def fetch_epic():
    try:
        data = fetch_epic_api("zh-CN", "CN")
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
            "image": get_epic_image(g),
            "url": get_epic_url(g),
            "originalPrice": orig,
            "discountPrice": disc,
            "originalPriceCNY": cents_to_cny(float(re.sub(r'[^0-9.]', '', orig)) * 100) if orig else "",
            "discountPriceCNY": cents_to_cny(float(re.sub(r'[^0-9.]', '', disc)) * 100) if disc else "",
            "seller": g.get("seller", {}).get("name", "")
        }
        
        for offer_set in offers:
            offer_list = offer_set.get("promotionalOffers", [])
            if offer_list:
                o = offer_list[0]
                discount_pct = o.get("discountSetting", {}).get("discountPercentage", -1)
                info["startDate"] = fmt_date(o.get("startDate", ""))
                info["endDate"] = fmt_date(o.get("endDate", ""))
                info["discount"] = 100 - discount_pct if discount_pct >= 0 else 0
                
                if discount_pct == 0:
                    free_games.append(info)
                elif discount_pct > 0:
                    discounts.append(info)
                break
    
    discounts.sort(key=lambda x: x.get("discount", 0), reverse=True)
    return {"free": free_games, "discounts": discounts}

# ═══════════════════════════════════════════
#  Steam 数据获取
# ═══════════════════════════════════════════

def fetch_steam():
    try:
        r = req.get(STEAM_API, params={"cc": "cn", "l": "schinese"}, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}", "free": [], "discounts": []}
        data = r.json()
    except Exception as e:
        return {"error": str(e), "free": [], "discounts": []}
    
    free_games, discounts = [], []
    seen_ids = set()
    
    # 遍历所有分类
    for cat_name, cat_data in data.items():
        if not isinstance(cat_data, dict) or "items" not in cat_data:
            continue
        for game in cat_data["items"]:
            game_id = game.get("id")
            if game_id in seen_ids:
                continue
            seen_ids.add(game_id)
            
            final_price = game.get("final_price", 0)
            is_free = game.get("is_free", False)
            discounted = game.get("discounted", False)
            discount_pct = game.get("discount_percent", 0)
            orig_price = game.get("original_price", 0)
            currency = game.get("currency", "CNY")
            
            # 免费游戏
            if final_price == 0 or is_free:
                free_games.append({
                    "id": str(game_id),
                    "title": game.get("name", "\u672a\u77e5\u6e38\u620f"),
                    "description": "",
                    "image": game.get("header_image") or game.get("small_capsule_image") or "",
                    "url": f"https://store.steampowered.com/app/{game_id}",
                    "originalPrice": cents_to_usd(orig_price) if orig_price else "",
                    "discountPrice": "\u514d\u8d39",
                    "originalPriceCNY": cents_to_cny(orig_price, currency) if orig_price else "",
                    "discountPriceCNY": "",
                    "seller": ""
                })
            # 折扣游戏
            elif discounted and discount_pct > 0:
                discounts.append({
                    "id": str(game_id),
                    "title": game.get("name", "\u672a\u77e5\u6e38\u620f"),
                    "description": "",
                    "image": game.get("header_image") or game.get("small_capsule_image") or "",
                    "url": f"https://store.steampowered.com/app/{game_id}",
                    "originalPrice": cents_to_usd(orig_price) if orig_price else "",
                    "discountPrice": cents_to_usd(final_price),
                    "originalPriceCNY": cents_to_cny(orig_price, currency) if orig_price else "",
                    "discountPriceCNY": cents_to_cny(final_price, currency),
                    "discount": discount_pct,
                    "seller": ""
                })
    
    discounts.sort(key=lambda x: x.get("discount", 0), reverse=True)
    return {"free": free_games, "discounts": discounts}

# ═══════════════════════════════════════════
#  前端页面
# ═══════════════════════════════════════════

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Epic & Steam \u4f18\u60e0\u67e5\u770b</title>
<style>
:root{--bg:#0a0a0f;--bg2:#12121a;--card:#1a1a2e;--t1:#e8e8f0;--t2:#8888a8;--blue:#0078f2;--green:#00d26a;--orange:#ff6b35;--purple:#7c3aed;--border:#2a2a40;--r:12px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif;background:var(--bg);color:var(--t1);min-height:100vh}
.header{background:linear-gradient(135deg,#0d0d1a,#1a1a35);border-bottom:1px solid var(--border);padding:1rem;position:sticky;top:0;z-index:100}
.header-inner{max-width:1400px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem}
.logo{display:flex;align-items:center;gap:.6rem}
.logo-icon{font-size:1.8rem}
.logo h1{font-size:1.2rem;font-weight:700;background:linear-gradient(135deg,var(--blue),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header-actions{display:flex;gap:.5rem}
.btn{padding:.45rem .8rem;border:1px solid var(--border);border-radius:8px;background:var(--card);color:var(--t1);cursor:pointer;font-size:.85rem}
.btn:hover{border-color:var(--blue)}
.tabs{max-width:1400px;margin:1rem auto 0;padding:0 1rem;display:flex;gap:.3rem;flex-wrap:wrap}
.tab{padding:.55rem 1rem;border:1px solid var(--border);border-radius:8px 8px 0 0;background:transparent;color:var(--t2);cursor:pointer;font-size:.85rem;border-bottom:none}
.tab.epic{--tab-color:var(--blue)}
.tab.steam{--tab-color:var(--purple)}
.tab.active{color:var(--t1);background:var(--bg2);border-color:var(--tab-color,var(--blue))}
.tab-name{font-weight:600}
.tab-badge{padding:.1rem .4rem;border-radius:8px;font-size:.7rem;margin-left:.3rem}
.tab.epic .tab-badge{background:rgba(0,120,242,.2);color:var(--blue)}
.tab.steam .tab-badge{background:rgba(124,58,237,.2);color:var(--purple)}
.main{max-width:1400px;margin:0 auto;padding:0 1rem 1.5rem}
.tab-content{display:none;background:var(--bg2);border:1px solid var(--border);border-radius:0 var(--r) var(--r) var(--r);padding:1.5rem}
.tab-content.active{display:block}
.sh{margin-bottom:1.2rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem}
.sh h2{font-size:1.3rem}
.sh h2 .brand{font-size:.9rem;padding:.2rem .6rem;border-radius:12px;margin-right:.5rem}
.sh h2 .brand.epic{background:rgba(0,120,242,.2);color:var(--blue)}
.sh h2 .brand.steam{background:rgba(124,58,237,.2);color:var(--purple)}
.grid{display:grid;gap:1rem}
.grid-3{grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
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
.price-wrap{display:flex;flex-direction:column;align-items:flex-end}
.price-orig{font-size:.7rem;color:var(--t2);text-decoration:line-through}
.price-new{color:var(--green);font-weight:700;font-size:.9rem}
.price-cny{font-size:.65rem;color:var(--t2)}
.loading{grid-column:1/-1;text-align:center;padding:3rem;color:var(--t2)}
.empty{grid-column:1/-1;text-align:center;padding:3rem;color:var(--t2)}
.empty .icon{font-size:2.5rem;margin-bottom:.8rem}
@media(max-width:768px){.grid-3{grid-template-columns:1fr}}
</style>
</head>
<body>
<header class="header"><div class="header-inner">
<div class="logo"><span class="logo-icon">\U0001f3ae</span><h1>Epic & Steam \u4f18\u60e0\u67e5\u770b</h1></div>
<div class="header-actions">
<button class="btn" onclick="loadAll()">\U0001f504 \u5237\u65b0</button>
</div>
</div></header>
<nav class="tabs">
<button class="tab epic active" onclick="switchTab('epic-free',this)"><span class="tab-name">\U0001f381 Epic</span><span class="tab-badge">\u514d\u8d39</span></button>
<button class="tab epic" onclick="switchTab('epic-deal',this)"><span class="tab-name">\U0001f4b0 Epic</span><span class="tab-badge">\u6298\u6263</span></button>
<button class="tab steam" onclick="switchTab('steam-free',this)"><span class="tab-name">\U0001f3ae Steam</span><span class="tab-badge">\u514d\u8d39</span></button>
<button class="tab steam" onclick="switchTab('steam-deal',this)"><span class="tab-name">\U0001f4b0 Steam</span><span class="tab-badge">\u6298\u6263</span></button>
</nav>
<main class="main">
<div id="tab-epic-free" class="tab-content active">
<div class="sh"><h2><span class="brand epic">Epic</span>\U0001f381 \u5f53\u524d\u514d\u8d39\u6e38\u620f</h2></div>
<div id="epic-free-list" class="grid grid-3"><div class="loading">\u52a0\u8f7d\u4e2d...</div></div>
</div>
<div id="tab-epic-deal" class="tab-content">
<div class="sh"><h2><span class="brand epic">Epic</span>\U0001f4b0 \u6298\u6263\u6e38\u620f</h2></div>
<div id="epic-deal-list" class="grid grid-3"><div class="loading">\u52a0\u8f7d\u4e2d...</div></div>
</div>
<div id="tab-steam-free" class="tab-content">
<div class="sh"><h2><span class="brand steam">Steam</span>\U0001f381 \u5f53\u524d\u514d\u8d39\u6e38\u620f</h2></div>
<div id="steam-free-list" class="grid grid-3"><div class="loading">\u52a0\u8f7d\u4e2d...</div></div>
</div>
<div id="tab-steam-deal" class="tab-content">
<div class="sh"><h2><span class="brand steam">Steam</span>\U0001f4b0 \u6298\u6263\u6e38\u620f</h2></div>
<div id="steam-deal-list" class="grid grid-3"><div class="loading">\u52a0\u8f7d\u4e2d...</div></div>
</div>
</main>
<script>
var data={epic:{free:[],deals:[]},steam:{free:[],deals:[]},loaded:{epic:false,steam:false}};
function $(id){return document.getElementById(id)}
function switchTab(name,el){
document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active')});
document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active')});
el.classList.add('active');
$('tab-'+name).classList.add('active');
}
function makeCard(g,type){
var c=document.createElement('a');c.className='gc';c.href=g.url;c.target='_blank';c.style.cssText='text-decoration:none;color:inherit';
var tag=type==='free'?'<span class="tag tag-free">\u514d\u8d39</span>':'<span class="tag tag-disc">-'+g.discount+'%</span>';
var price=type==='free'?
'<div class="price-wrap"><span class="price-new">\u514d\u8d39</span></div>':
'<div class="price-wrap"><span class="price-orig">'+g.originalPrice+'</span><span class="price-new">'+g.discountPrice+'</span><span class="price-cny">'+g.discountPriceCNY+'</span></div>';
c.innerHTML='<img src="'+g.image+'" onerror="this.src=\'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 320 140%22><rect fill=%22%231a1a2e%22 width=%22320%22 height=%22140%22/><text x=%2250%25%22 y=%2250%25%22 fill=%22%238888a8%22 text-anchor=%22middle%22 dy=%22.3em%22 font-size=%2214%22>\u6e38\u620f\u56fe</text></svg>\'">'+'<div class="gc-body"><div class="gc-title">'+g.title+'</div><div class="gc-desc">'+g.description+'</div><div class="gc-foot">'+tag+price+'</div></div>';
return c;
}
function showList(el,list,type){
if(list.length===0){
el.innerHTML='<div class="empty"><div class="icon">\U0001f50d</div><p>\u6682\u65e0\u6570\u636e</p></div>';
return;
}
el.innerHTML='';
list.forEach(function(g){el.appendChild(makeCard(g,type));});
}
function loadEpic(){
fetch('/api/epic').then(function(r){return r.json()}).then(function(d){
if(d.error){$('epic-free-list').innerHTML='<div class="empty"><div class="icon">\u26a0\ufe0f</div><p>'+d.error+'</p></div>';return;}
data.epic=d;data.loaded.epic=true;
showList($('epic-free-list'),d.free,'free');
showList($('epic-deal-list'),d.discounts,'deal');
}).catch(function(){$('epic-free-list').innerHTML='<div class="empty"><div class="icon">\u274c</div><p>\u7f51\u7edc\u9519\u8bef</p></div>';});
}
function loadSteam(){
fetch('/api/steam').then(function(r){return r.json()}).then(function(d){
if(d.error){$('steam-free-list').innerHTML='<div class="empty"><div class="icon">\u26a0\ufe0f</div><p>'+d.error+'</p></div>';return;}
data.steam=d;data.loaded.steam=true;
showList($('steam-free-list'),d.free,'free');
showList($('steam-deal-list'),d.discounts,'deal');
}).catch(function(){$('steam-free-list').innerHTML='<div class="empty"><div class="icon">\u274c</div><p>\u7f51\u7edc\u9519\u8bef</p></div>';});
}
function loadAll(){loadEpic();loadSteam();}
loadAll();
</script>
</body></html>"""

# ═══════════════════════════════════════════
#  Flask 路由
# ═══════════════════════════════════════════

@app.route("/")
def index():
    return HTML

@app.route("/api/epic")
def api_epic():
    return jsonify(fetch_epic())

@app.route("/api/steam")
def api_steam():
    return jsonify(fetch_steam())

@app.route("/api/notifications", methods=["POST"])
def api_notify():
    data = request.get_json(force=True)
    notified = load_json(NOTIFY_FILE, {"ids": []})
    if data.get("action") == "check":
        epic = fetch_epic()
        new_ids = [g["id"] for g in epic.get("free", []) if g["id"] not in notified["ids"]]
        for gid in new_ids:
            notified["ids"].append(gid)
        save_json(NOTIFY_FILE, notified)
        return jsonify({"new_count": len(new_ids)})
    return jsonify({"error": "unknown"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
