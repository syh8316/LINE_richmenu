# syh/deploy_richmenu_alias.py
import os, sys, json, argparse, requests
from PIL import Image

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
    
def build_areas():
    return [
        {"bounds": {"x": X_OFF[0], "y": 0, "width": COL_W[0], "height": TAB_H},
         "action": {"type": "richmenuswitch", "richMenuAliasId": "menu-a", "data": "goto=menuA"}},
        {"bounds": {"x": X_OFF[1], "y": 0, "width": COL_W[1], "height": TAB_H},
         "action": {"type": "richmenuswitch", "richMenuAliasId": "menu-b", "data": "goto=menuB"}},
        {"bounds": {"x": X_OFF[2], "y": 0, "width": COL_W[2], "height": TAB_H},
         "action": {"type": "message", "text": "選單 C（尚未製作）"}},
    ]

def create_menu(token, name, chatbar, areas):
    HJ = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    body = {"size": {"width": W, "height": H}, "selected": False,
            "name": name, "chatBarText": chatbar, "areas": areas}
    r = requests.post(f"{API}/richmenu", headers=HJ, data=json.dumps(body).encode("utf-8"))
    must_ok(r, f"create {name}")
    rid = r.json()["richMenuId"]
    print(f"[OK] created {name}: {rid}")
    return rid

def upload_image(token, richmenu_id, image_path):
    HB = {'Authorization': f'Bearer {token}', 'Content-Type': 'image/jpeg'}
    with open(image_path, "rb") as f:
        r = requests.post(f"{API_DATA}/richmenu/{richmenu_id}/content", headers=HB, data=f.read())
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
            data=json.dumps({"richMenuAliasId": alias_id, "richMenuId": richmenu_id}).encode("utf-8")
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
                data=json.dumps({"richMenuAliasId": alias_id, "richMenuId": richmenu_id}).encode("utf-8")
            )
            must_ok(r_new, f"create alias {alias_id} (after 400)")
            print(f"[OK] alias created(after 400): {alias_id} -> {richmenu_id}")
        else:
            must_ok(r_upd, f"update alias {alias_id}")

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--imageA", default="richmenu/line/menuA.png")
    ap.add_argument("--imageB", default="richmenu/line/menuB.png")
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

def main():
    token = os.environ.get("LINE_TOKEN")
    if not token:
        print("請用環境變數 LINE_TOKEN 提供 Channel access token"); sys.exit(1)

    args = parse_args()

    # ✨ 這裡改成自動裁切
    imgA = fit_contain(args.imageA)
    imgB = fit_contain(args.imageB)

    areas = build_areas()

    rid_a = create_menu(token, "選單A", args.chatbar, areas); upload_image(token, rid_a, imgA)
    rid_b = create_menu(token, "選單B", args.chatbar, areas); upload_image(token, rid_b, imgB)

    create_or_update_alias(token, "menu-a", rid_a)
    create_or_update_alias(token, "menu-b", rid_b)

    set_default_all(token, rid_a if args.__dict__["set_default"] == "menu-a" else rid_b)

    if args.delete_others:
        keep = {rid_a, rid_b}
        for m in list_menus(token):
            if m["richMenuId"] not in keep:
                delete_menu(token, m["richMenuId"])

    print("\n[完成] 用手機開和機器人 1:1 聊天 → 點上方『選單 A / 選單 B』即可切換。")

if __name__ == "__main__":
    main()
