# daily_push.py
import os, json, requests, sys
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

API = "https://api.line.me/v2/bot"
HDR_JSON = lambda token: {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
HDR_GET  = lambda token: {"Authorization": f"Bearer {token}"}

def must_ok(r, what):
    if not r.ok:
        print(f"[ERROR] {what}: {r.status_code} {r.text}")
        sys.exit(1)
    else:
        rid = r.headers.get("X-Line-Request-Id", "-")
        print(f"[OK] {what} (X-Line-Request-Id: {rid})")

def make_default_text():
    tz = ZoneInfo("Asia/Taipei")
    now = datetime.now(tz)
    wd = ["一","二","三","四","五","六","日"][(now.weekday())]  # 0=Mon
    hour = now.hour
    greet = "早安" if 5 <= hour < 12 else ("午安" if 12 <= hour < 18 else "晚安")
    base = os.getenv("MESSAGE", "祝你順心 😊")
    return f"{greet}～今天是 {now:%Y-%m-%d}（{wd}）\n{base}"

def send_broadcast(token, text):
    url = f"{API}/message/broadcast"
    body = {"messages": [{"type": "text", "text": text}]}
    r = requests.post(url, headers=HDR_JSON(token), data=json.dumps(body).encode("utf-8"))
    must_ok(r, "broadcast")

def send_multicast(token, user_ids, text):
    # Multicast 最多一次 500 人，如超過請自行分批
    url = f"{API}/message/multicast"
    body = {"to": user_ids, "messages": [{"type": "text", "text": text}]}
    r = requests.post(url, headers=HDR_JSON(token), data=json.dumps(body).encode("utf-8"))
    must_ok(r, f"multicast ({len(user_ids)} users)")

def list_followers(token, limit=1000):
    # 逐頁取用戶 ID：/v2/bot/followers/ids
    # 官方參考：Getting user IDs（含 followers/ids 說明）
    url = f"{API}/followers/ids"
    params = {"limit": limit}
    ids, start = [], None
    while True:
        if start: params["start"] = start
        r = requests.get(url, headers=HDR_GET(token), params=params)
        must_ok(r, "get followers/ids")
        data = r.json()
        ids.extend(data.get("userIds", []))
        start = data.get("next")
        if not start: break
    return ids

def main():
    token = os.getenv("LINE_TOKEN")
    if not token:
        print("請以環境變數 LINE_TOKEN 提供 Channel access token")
        sys.exit(1)

    text = make_default_text()
    mode = os.getenv("MODE", "broadcast").lower()

    if mode == "broadcast":
        send_broadcast(token, text)
    elif mode in ("multicast", "push"):
        raw = os.getenv("USER_IDS", "")
        if raw.strip():
            ids = [s.strip() for s in raw.split(",") if s.strip()]
        else:
            print("[Info] 未提供 USER_IDS，改用 followers API 取得所有好友 id …")
            ids = list_followers(token)
        # 分批最多 500 人
        for i in range(0, len(ids), 500):
            send_multicast(token, ids[i:i+500], text)
    else:
        print(f"未知 MODE='{mode}'（允許 broadcast / multicast / push）")
        sys.exit(1)

if __name__ == "__main__":
    main()
