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

# ---------- Message builders ----------
def make_default_text():
    tz = ZoneInfo("Asia/Taipei")
    now = datetime.now(tz)
    wd = ["一","二","三","四","五","六","日"][now.weekday()]  # Mon=0
    hour = now.hour
    greet = "早安" if 5 <= hour < 12 else ("午安" if 12 <= hour < 18 else "晚安")
    base = os.getenv("MESSAGE", "祝你順心 😊")
    return f"{greet}～今天是 {now:%Y-%m-%d}（{wd}）\n{base}"

# ---------- Senders ----------
def send_broadcast(token, text):
    url = f"{API}/message/broadcast"
    body = {"messages": [{"type": "text", "text": text}]}
    r = requests.post(url, headers=HDR_JSON(token), data=json.dumps(body).encode("utf-8"))
    must_ok(r, "broadcast")

def send_multicast(token, user_ids, text):
    url = f"{API}/message/multicast"
    body = {"to": user_ids, "messages": [{"type": "text", "text": text}]}
    r = requests.post(url, headers=HDR_JSON(token), data=json.dumps(body).encode("utf-8"))
    must_ok(r, f"multicast ({len(user_ids)} users)")

# ---------- Helpers ----------
def list_followers(token, limit=1000):
    url = f"{API}/followers/ids"
    params, ids, start = {"limit": limit}, [], None
    while True:
        if start: params["start"] = start
        r = requests.get(url, headers=HDR_GET(token), params=params)
        must_ok(r, "get followers/ids")
        data = r.json()
        ids.extend(data.get("userIds", []))
        start = data.get("next")
        if not start: break
    return ids

def get_month_quota(token):
    """Return (quota_type, quota_value or None)
       quota_type: 'limited' / 'unlimited' / 'none'(某些方案)
       quota_value: 當月可用總額度（僅 limited 時有數字）
    """
    r = requests.get(f"{API}/message/quota", headers=HDR_GET(token))
    must_ok(r, "get monthly quota")
    data = r.json()
    qtype = data.get("type")
    qval  = data.get("value") if qtype == "limited" else None
    return qtype, qval

def get_month_consumption(token):
    """Return totalUsage（本月已用量）"""
    r = requests.get(f"{API}/message/quota/consumption", headers=HDR_GET(token))
    must_ok(r, "get monthly consumption")
    data = r.json()
    return int(data.get("totalUsage", 0))

def should_skip_by_quota(token, expected_cost=0):
    """依環境變數決定是否跳過發送"""
    stop_percent = float(os.getenv("QUOTA_STOP_PERCENT", "0.95"))  # 95%
    min_remain   = int(os.getenv("QUOTA_MIN_REMAIN", "0"))         # 例如保留 500 則
    qtype, qval  = get_month_quota(token)
    used         = get_month_consumption(token)

    if qtype != "limited" or not qval:
        print(f"[Quota] type={qtype}（無上限或無需計）→ 不啟動保護，繼續。")
        return False

    remain = int(qval) - int(used)
    ratio  = used / qval if qval else 0.0
    print(f"[Quota] plan={qtype}, quota={qval}, used={used}, remain={remain}, ratio={ratio:.3f}")

    reasons = []
    if ratio >= stop_percent:
        reasons.append(f"已用量比例 {ratio:.1%} ≥ 門檻 {stop_percent:.0%}")
    if remain <= min_remain:
        reasons.append(f"剩餘 {remain} ≤ 保留下限 {min_remain}")
    if expected_cost and expected_cost > remain:
        reasons.append(f"本次預估需 {expected_cost} > 剩餘 {remain}")

    if reasons:
        print("[Skip] 觸發配額保護，不發送。原因： " + "；".join(reasons))
        return True
    return False

def main():
    token = os.getenv("LINE_TOKEN")
    if not token:
        print("請以環境變數 LINE
