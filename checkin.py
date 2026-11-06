#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib, os, re, sys, time
from datetime import datetime, timedelta, timezone
import requests

BASE = os.getenv("GLADOS_DOMAIN", "https://glados.network")
TOKEN = BASE.split("//")[1]          # 必须与域名一致，否则服务端回 "please checkin via <domain>"
PROOF_SALT = "glados-observe-v1"     # 前端 checkinProof() 里写死的盐

def log(msg): print(f"[{datetime.now(timezone(timedelta(hours=8))):%Y-%m-%d %H:%M:%S}] {msg}", flush=True)

def get_cookie():
    raw = os.getenv("GLADOS_COOKIE", "").strip()
    if raw:
        return re.sub(r"^cookie\s*:\s*", "", raw, flags=re.I)
    sess, sig = os.getenv("GLD_SESS"), os.getenv("GLD_SESS_SIG")
    if sess and sig:
        return f"gld:sess={sess}; gld:sess.sig={sig}"
    raise SystemExit("缺少 GLADOS_COOKIE（整行 cookie，含 gld:sess 与 gld:sess.sig）")

def build_headers(ua):
    h = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/json;charset=UTF-8",
        "origin": BASE,
        "referer": f"{BASE}/console/checkin",   # 旧脚本漏了这个
        "user-agent": ua,
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    m = re.search(r"Chrome/(\d+)", ua)          # 让 sec-ch-ua 与 UA 自洽
    if m:
        v, plat = m.group(1), (
            "macOS" if "Macintosh" in ua else "Windows" if "Windows" in ua
            else "Android" if "Android" in ua else "Linux" if "Linux" in ua else "Unknown")
        h["sec-ch-ua"] = f'"Chromium";v="{v}", "Google Chrome";v="{v}", "Not_A Brand";v="99"'
        h["sec-ch-ua-mobile"] = "?1" if "Mobile" in ua else "?0"
        h["sec-ch-ua-platform"] = f'"{plat}"'
    return h

def make_proof(nonce: str) -> str:
    """与前端 checkinProof 等价：SHA256(nonce + "." + salt) 的 hex"""
    return hashlib.sha256(f"{nonce}.{PROOF_SALT}".encode()).hexdigest()

def get_challenge(s):
    r = s.get(f"{BASE}/api/user/checkin/challenge", timeout=15)
    r.raise_for_status()
    js = r.json()
    log(f"challenge: nonce={str(js.get('nonce'))[:8]}… ttl={js.get('ttl')}")
    return js.get("nonce"), js.get("ttl")

def classify(res):
    msg = str(res.get("message", "")).lower()
    if any(k in msg for k in ("checkin! got", "checkin repeats", "observation logged")):
        return "ok"
    if any(k in msg for k in ("automated check-in detected", "没有权限", "permission", "unauthorized")):
        return "denied"            # 认证/设备被拒，重试无用
    if res.get("code") in (-2,) or "device" in str(res.get("reason", "")):
        return "denied"
    return "retry"

def checkin(s):
    nonce, _ = get_challenge(s)
    payload = {"token": TOKEN}
    if nonce:
        payload.update({"nonce": nonce, "proof": make_proof(nonce)})
    r = s.post(f"{BASE}/api/user/checkin", json=payload, timeout=20)
    if r.status_code in (401, 403):
        log(f"HTTP {r.status_code}: {r.text[:200]}")
    r.raise_for_status()
    return r.json()

def main():
    ua = os.getenv("GLADOS_UA", "").strip()
    if not ua:
        log("⚠️ 未配置 GLADOS_UA：会用默认 UA，和生成 cookie 的浏览器不一致时会被判 device-mismatch")
        ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36")
    s = requests.Session()
    s.headers.update(build_headers(ua))
    s.headers["cookie"] = get_cookie()

    res = None
    for i in range(1, 4):
        try:
            res = checkin(s)
        except requests.RequestException as e:
            log(f"第 {i}/3 次请求异常: {e}")
            time.sleep(30); continue
        kind = classify(res)
        log(f"响应: {res}")                  # 完整打印，用来确认 base/分项奖励字段
        if kind == "ok":
            log("✅ 签到完成"); break
        if kind == "denied":
            log("❌ 被服务端拒绝（会话/设备不匹配），重试无效，请更新 cookie 与 UA"); return 1
        log(f"⚠️ 第 {i}/3 次失败，30 秒后重试"); time.sleep(30)
    else:
        log("❌ 三次均失败"); return 1

    st = s.get(f"{BASE}/api/user/status", timeout=15).json().get("data", {})
    pt = s.get(f"{BASE}/api/user/points", timeout=15).json()
    log(f"积分: {pt.get('points')}  剩余天数: {st.get('leftDays')}  连续签到: {pt.get('streak')}")
    return 0

if __name__ == "__&#8203;main__":
    sys.exit(main())
