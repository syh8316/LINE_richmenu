# deploy_richmenu.py
import os, json, argparse, sys
import requests
from PIL import Image

API = "https://api.line.me/v2/bot"
API_DATA = "https://api-data.line.me/v2/bot"

def must_ok(r, msg):
    if not r.ok:
        print(f"[ERROR] {msg}: {r.status_code} {r.text}")
        sys.exit(1)

def create_menu(token, name, chatbar, home_url, fb_url, ig_url, threads_url):
    HJ = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    body = {
        'size': {'width': 2500, 'height': 1686},
        'selected': True,
        'name': name,
        'chatBarText': chatbar,
        'areas': [
            {'bounds': {'x': 0, 'y': 0, 'width': 2500, 'height': 843},
             'action': {'type': 'uri', 'label': '新義和歌劇團', 'uri': home_url}},
            {'bounds': {'x': 0, 'y': 843, 'width': 833, 'height': 843},
             'action': {'type': 'uri', 'label': 'FB', 'uri': fb_url}},
            {'bounds': {'x': 833, 'y': 843, 'width': 834, 'height': 843},
             'action': {'type': 'uri', 'label': 'IG', 'uri': ig_url}},
            {'bounds': {'x': 1667, 'y': 843, 'width': 833, 'height': 843},
             'action': {'type': 'uri', 'label': 'Threads', 'uri': threads_url}},
        ]
    }
    r = requests.post(f"{API}/richmenu", headers=HJ, data=json.dumps(body).encode("utf-8"))
    must_ok(r, "create richmenu")
    rid = r.json()["richMenuId"]
    print("[OK] created:", rid)
    return rid

def upload_image(token, richmenu_id, image_path):
    HB = {'Authorization': f'Bearer {token}', 'Content-Type': 'image/jpeg'}
    w, h = Image.open(image_path).size
    assert (w, h) == (2500, 1686), f"圖片需 2500x1686，現在是 {w}x{h}"
    with open(image_path, "rb") as f:
        r = requests.post(f"{API_DATA}/richmenu/{richmenu_id}/content", headers=HB, data=f.read())
    must_ok(r, "upload image")
    print("[OK] uploaded image to", richmenu_id)

def set_default_all(token, richmenu_id):
    H = {'Authorization': f'Bearer {token}'}
    r = requests.post(f"{API}/user/all/richmenu/{richmenu_id}", headers=H)
    must_ok(r, "set default(all)")
    print("[OK] set default(all):", richmenu_id)

def get_default_all(token):
    H = {'Authorization': f'Bearer {token}'}
    r = requests.get(f"{API}/user/all/richmenu", headers=H)
    if r.status_code == 200:
        rid = r.json().get("richMenuId")
        print("[OK] current default(all):", rid)
        return rid
    print("[INFO] default(all): none")
    return None

def list_menus(token):
    H = {'Authorization': f'Bearer {token}'}
    r = requests.get(f"{API}/richmenu/list", headers=H)
    must_ok(r, "list menus")
    return r.json().get("richmenus", [])

def delete_menu(token, richmenu_id):
    H = {'Authorization': f'Bearer {token}'}
    r = requests.delete(f"{API}/richmenu/{richmenu_id}", headers=H)
    must_ok(r, f"delete {richmenu_id}")
    print("[OK] deleted:", richmenu_id)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="syh/line/richmenu_comp.jpg")
    parser.add_argument("--name", default="劇團資訊")
    parser.add_argument("--chatbar", default="劇團資訊")
    parser.add_argument("--home", default="https://syh8316.github.io/syh8316/syh/home.html")
    parser.add_argument("--fb", default="https://www.facebook.com/share/1AQhTBMEyT/?mibextid=wwXIfr")
    parser.add_argument("--ig", default="https://www.instagram.com/syh.ot_1994?utm_source=qr")
    parser.add_argument("--threads", default="https://www.threads.net/@syh.ot_1994")
    parser.add_argument("--delete-others", action="store_true", help="建立後刪除舊選單")
    parser.add_argument("--set-default", action="store_true", help="建立後設為全體預設")
    args = parser.parse_args()

    token = os.environ.get("LINE_TOKEN")
    if not token:
        print("請以環境變數 LINE_TOKEN 提供 Channel access token")
        sys.exit(1)

    # 建立 → 上傳圖 → （選擇性）設全體預設 → （選擇性）刪舊的
    new_id = create_menu(token, args.name, args.chatbar, args.home, args.fb, args.ig, args.threads)
    upload_image(token, new_id, args.image)

    if args.set_default:
        set_default_all(token, new_id)
        get_default_all(token)

    if args.delete_others:
        menus = list_menus(token)
        for m in menus:
            if m["richMenuId"] != new_id:
                delete_menu(token, m["richMenuId"])

if __name__ == "__main__":
    main()
