# syh/deploy_richmenu_alias.py
import os, sys, json, argparse, requests
from PIL import Image
from pathlib import Path

API = "https://api.line.me/v2/bot"
API_DATA = "https://api-data.line.me/v2/bot"

W, H = 2500, 1686            # Rich menu 大尺寸
TAB_H = 250                  # 上方切換列高度
COL_W = [833, 834, 833]      # 三等分寬
X_OFF = [0, 833, 1667]

def must_ok(r, msg):
    if not r.ok:
        print(f"[ERROR] {msg}: {r.status_code} {r.text}")
        sys.exit(1)

def fit_contain(path, tw=W, th=H, bg=(0,0,0)):
    """把圖等比縮放到剛好放得下（不裁切），不足的邊留背景色。"""
    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    s = min(tw/iw, th/ih)             # 注意這裡是 min → 不裁切
    nw, nh = int(iw*s), int(ih*s)
    resized = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (tw, th), bg)
    left = (tw - nw)//2
    top  = (th - nh)//2
    canvas.paste(resized, (left, top))
    out = f"/tmp/{os.path.basename(path).rsplit('.',1)[0]}_contain.jpg"
    canvas.save(out, quality=90)
    print(f"[OK] fitted (contain) to {tw}x{th} -> {out}")
    return out

def ensure_path(p):
    q = Path(p)
    print(f"[DEBUG] image path = {q} (abs={q.resolve()}) exists={q.exists()}")
    if not q.exists():
        raise FileNotFoundError(f"找不到圖片: {q}")
    return str(q)

def areas_menu_a():
    """A頁：基本資訊（聯絡／最新活動／樂師／演員）"""
    return [
        # 分頁列（左=當前A、右=切到B）
        {"bounds":{"x":0,    "y":0, "width":1250, "height":TAB_H},
         "action":{"type":"richmenuswitch","richMenuAliasId":"menu-a","data":"tab=a"}},
        {"bounds":{"x":1250, "y":0, "width":1250, "height":TAB_H},
         "action":{"type":"richmenuswitch","richMenuAliasId":"menu-b","data":"tab=b"}},

        # 內容 2×2
        {"bounds":{"x":0,    "y":TAB_H,        "width":1250, "height":718},
         "action":{"type":"postback","data":"sec=contact"}},                 # 聯絡資訊
        {"bounds":{"x":1250, "y":TAB_H,        "width":1250, "height":718},
         "action":{"type":"postback","data":"sec=events&page=1"}},           # 最新活動

        {"bounds":{"x":0,    "y":TAB_H+718,    "width":1250, "height":718},
         "action":{"type":"postback","data":"sec=musicians&page=1"}},        # 樂師資訊
        {"bounds":{"x":1250, "y":TAB_H+718,    "width":1250, "height":718},
         "action":{"type":"postback","data":"sec=actors&page=1"}}            # 演員資訊
    ]

def areas_menu_b():
    """B頁：連結資訊（上排整條官網；下排 FB/IG/Threads）"""
    return [
        # 分頁列（左=切到A、右=當前B）
        {"bounds": {"x": 0,    "y": 0, "width": 1250, "height": TAB_H},
         "action": {"type": "richmenuswitch", "richMenuAliasId": "menu-a", "data": "tab=a"}},
        {"bounds": {"x": 1250, "y": 0, "width": 1250, "height": TAB_H},
         "action": {"type": "richmenuswitch", "richMenuAliasId": "menu-b", "data": "tab=b"}},

        # 1~3：整條（官網）
        {"bounds": {"x": 0, "y": TAB_H, "width": 2500, "height": 718},
         "action": {"type": "uri", "label": "官網",
                    "uri": "https://syh8316.github.io/syh8316/syh/home.html"}},

        # 4：左下（FB）
        {"bounds": {"x": 0, "y": TAB_H + 718, "width": 833, "height": 718},
         "action": {"type": "uri", "label": "Facebook",
                    "uri": "https://www.facebook.com/p/%E6%96%B0%E7%BE%A9%E5%92%8C%E6%AD%8C%E5%8A%87%E5%9C%98-100065152267273/?locale=zh_TW"}},

        # 5：中下（IG）
        {"bounds": {"x": 833, "y": TAB_H + 718, "width": 834, "height": 718},
         "action": {"type": "uri", "label": "Instagram",
                    "uri": "https://www.instagram.com/syh.ot_1994/"}},

        # 6：右下（Threads）
        {"bounds": {"x": 1667, "y": TAB_H + 718, "width": 833, "height": 718},
         "action": {"type": "uri", "label": "Threads",
                    "uri": "https://www.threads.net/@syh.ot_1994"}}
    ]
    
def create_menu(token, name, chatbar, areas):
    HJ = {'Authorization': f'Bearer {token}', 
          'Content-Type': 'application/json'
         }
    body = {"size": {"width": W, "height": H},
            "selected": True,
            "name": name, 
            "chatBarText": chatbar, 
            "areas": areas
           }
    r = requests.post(f"{API}/richmenu", 
                      headers=HJ,
                      data=json.dumps(body).encode("utf-8")
                     )
    must_ok(r, f"create {name}")
    rid = r.json()["richMenuId"]
    print(f"[OK] created {name}: {rid}")
    return rid

def upload_image(token, richmenu_id, image_path):
    HB = {'Authorization': f'Bearer {token}', 'Content-Type': 'image/jpeg'}
    with open(image_path, "rb") as f:
        r = requests.post(f"{API_DATA}/richmenu/{richmenu_id}/content", 
                          headers=HB, data=f.read()
                         )
    must_ok(r, f"upload image -> {richmenu_id}")
    print(f"[OK] image uploaded -> {richmenu_id}")

def set_default_all(token, richmenu_id):
    H = {'Authorization': f'Bearer {token}'}
    r = requests.post(f"{API}/user/all/richmenu/{richmenu_id}", headers=H)
    must_ok(r, "set default(all)")
    print("[OK] set default(all):", richmenu_id)

def create_or_update_alias(token, alias_id, richmenu_id):
    HJ = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    # 先嘗試「更新」既有 alias
    r_upd = requests.post(
        f"{API}/richmenu/alias/{alias_id}",
        headers=HJ,
        data=json.dumps({"richMenuId": richmenu_id}).encode("utf-8")
    )
    if r_upd.status_code == 404:
        # 不存在 → 改為「建立」
        r_new = requests.post(
            f"{API}/richmenu/alias",
            headers=HJ,
            data=json.dumps({"richMenuAliasId": alias_id, 
                             "richMenuId": richmenu_id}).encode("utf-8")
                            )
        must_ok(r_new, f"create alias {alias_id}")
        print(f"[OK] alias created: {alias_id} -> {richmenu_id}")
    elif r_upd.ok:
        print(f"[OK] alias updated: {alias_id} -> {richmenu_id}")
    else:
        # 少數情況 API 會回 400 conflict；再補一次 create 或顯示錯誤
        txt = r_upd.text.lower()
        if r_upd.status_code == 400 and "conflict" in txt:
            # 既有但無法直接更新，改走建立（若仍衝突，請用方案2刪除）
            r_new = requests.post(
                f"{API}/richmenu/alias",
                headers=HJ,
                data=json.dumps({"richMenuAliasId": alias_id, 
                                 "richMenuId": richmenu_id}).encode("utf-8")
                                )   
            must_ok(r_new, f"create alias {alias_id} (after 400)")
            print(f"[OK] alias created(after 400): {alias_id} -> {richmenu_id}")
        else:
            must_ok(r_upd, f"update alias {alias_id}")

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--imageA", default="richmenu/line/menu_1.PNG")
    ap.add_argument("--imageB", default="richmenu/line/menu_2.PNG")
    ap.add_argument("--chatbar", default="劇團資訊")
    ap.add_argument("--set-default", choices=["menu-a", "menu-b"], default="menu-a")
    ap.add_argument("--delete-others", action="store_true")
    return ap.parse_args()

def list_menus(token):
    H = {'Authorization': f'Bearer {token}'}
    r = requests.get(f"{API}/richmenu/list", headers=H)
    must_ok(r, "list menus")
    return r.json().get("richmenus", [])

def delete_menu(token, rid):
    H = {'Authorization': f'Bearer {token}'}
    r = requests.delete(f"{API}/richmenu/{rid}", headers=H)
    must_ok(r, f"delete {rid}")
    print("[OK] deleted:", rid)

def list_aliases(token):
    H = {'Authorization': f'Bearer {token}'}
    r = requests.get(f"{API}/richmenu/alias/list", headers=H)
    must_ok(r, "list aliases")
    return r.json().get("aliases", [])

def delete_alias(token, alias_id):
    H = {'Authorization': f'Bearer {token}'}
    r = requests.delete(f"{API}/richmenu/alias/{alias_id}", headers=H)
    must_ok(r, f"delete alias {alias_id}")
    print("[OK] alias deleted:", alias_id)

def main():
    token = os.environ.get("LINE_TOKEN")
    if not token:
        print("請用環境變數 LINE_TOKEN 提供 Channel access token"); sys.exit(1)

    args = parse_args()

    # （可選）先清掉舊 alias，避免衝突
    try:
        for a in list_aliases(token):
            alias = a.get("richMenuAliasId")
            if alias in {"menu-a", "menu-b"}:
                delete_alias(token, alias)
    except Exception as e:
        print("[WARN] skip alias cleanup:", e)

    # 圖片等比縮放（不裁切）
    imgA = fit_contain(ensure_path(args.imageA), bg=(238,236,226))
    imgB = fit_contain(ensure_path(args.imageB), bg=(238,236,226))

    areasA = areas_menu_a()
    areasB = areas_menu_b()
    
    rid_a = create_menu(token, "基本資訊", args.chatbar, areasA); upload_image(token, rid_a, imgA)
    rid_b = create_menu(token, "連結資訊", args.chatbar, areasB); upload_image(token, rid_b, imgB)
    
    create_or_update_alias(token, "menu-a", rid_a)
    create_or_update_alias(token, "menu-b", rid_b)

    # 設定/更新 alias
    create_or_update_alias(token, "menu-a", rid_a)
    create_or_update_alias(token, "menu-b", rid_b)

    # 設成全體預設
    set_default_all(token, rid_a if args.__dict__["set_default"] == "menu-a" else rid_b)

    # （可選）刪掉其他非 A/B 的舊選單
    if args.delete_others:
        keep = {rid_a, rid_b}
        for m in list_menus(token):
            if m["richMenuId"] not in keep:
                delete_menu(token, m["richMenuId"])

    print("\n[完成] 用手機開和機器人 1:1 聊天 → 點上方『選單 A / 選單 B』即可切換。")

if __name__ == "__main__":
    main()
