#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

# =================  =================
BASE = "https://glados.network"   # 
# ======================================================

PROOF_SALT = "glados-observe-v1"
TIMEOUT = 15
SLEEP_BETWEEN_ACCOUNTS = 8
DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

TOKEN = BASE.split("//")[-1].split("/")[0]

OK_WORDS = ("checkin! got", "checkin repeats", "observation logged")
DENY_WORDS = ("automated check-in detected", "没有权限", "permission",
              "unauthorized", "device-mismatch")

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass


def log(msg=""):
    if not msg:
        print("", flush=True)
        return
    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_accounts():
    """返回 [(cookie, ua), ...]，多账号用换行分隔"""
    raw = os.getenv("GLADOS_COOKIE", "").strip()
    ua_raw = (os.getenv("GLADOS_UA") or os.getenv("GLADOS_USER_AGENT") or "").strip()

    if raw:
        cookies = [c.strip() for c in re.split(r"[\r\n]+", raw) if c.strip()]
    else:  # 兼容你原来那两个 secret
        sess = os.getenv("SESSION_COOKIE", "").strip()
        sig = os.getenv("SESSION_SIG", "").strip()
        cookies = [f"gld:sess={sess}; gld:sess.sig={sig}"] if sess and sig else []

    if not cookies:
        log("❌ 没拿到 cookie：配 GLADOS_COOKIE（整行）或 SESSION_COOKIE + SESSION_SIG")
        return []

    uas = [u.strip() for u in re.split(r"[\r\n]+", ua_raw) if u.strip()]
    accounts = []
    for i, c in enumerate(cookies):
        c = re.sub(r"^cookie\s*:\s*", "", c, flags=re.I)
        ua = uas[i] if i < len(uas) else (uas[0] if uas else DEFAULT_UA)
        accounts.append((c, ua))
    return accounts


def build_headers(ua, cookie):
    h = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/json;charset=UTF-8",
        "origin": BASE,
        "referer": f"{BASE}/console/checkin",
        "user-agent": ua,
        "cookie": cookie,
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }
    m = re.search(r"Chrome/(\d+)", ua)
    if m:
        v = m.group(1)
        plat = "Windows"
        if "Macintosh" in ua:
            plat = "macOS"
        elif "Android" in ua:
            plat = "Android"
        elif "Linux" in ua:
            plat = "Linux"
        h["sec-ch-ua"] = f'"Chromium";v="{v}", "Google Chrome";v="{v}", "Not_A Brand";v="99"'
        h["sec-ch-ua-mobile"] = "?1" if "Mobile" in ua else "?0"
        h["sec-ch-ua-platform"] = f'"{plat}"'
    return h


def handle_account(idx, cookie, ua):
    log("=" * 60)
    log(f"账号 {idx} 开始")
    s = requests.Session()
    s.headers.update(build_headers(ua, cookie))

    # 1) 先确认会话有效
    try:
        st = s.get(f"{BASE}/api/user/status", timeout=TIMEOUT).json()
    except Exception as e:
        log(f"  ❌ 查询状态失败（网络）：{e}")
        return False
    if st.get("code") != 0:
        log(f"  ❌ 会话无效：{st.get('message') or st}")
        log("     → 需要重新复制整行 cookie（含 gld:sess.sig）")
        return False
    d = st.get("data", {})
    log(f"  会话正常 | 剩余天数 {d.get('leftDays')} | vip {d.get('vip')}")

    # 2) 取挑战 nonce
    nonce = ""
    try:
        nonce = s.get(f"{BASE}/api/user/checkin/challenge", timeout=TIMEOUT).json().get("nonce", "")
        log(f"  challenge nonce 已获取")
    except Exception as e:
        log(f"  ⚠️ 取 challenge 失败，按旧方式签到：{e}")

    # 3) 签到（字段组合依次尝试）
    payloads = []
    if nonce:
        proof = hashlib.sha256(f"{nonce}.{PROOF_SALT}".encode()).hexdigest()
        payloads = [
            {"token": TOKEN, "nonce": nonce, "proof": proof},
            {"token": TOKEN, "challenge": nonce, "proof": proof},
            {"token": TOKEN, "nonce": nonce, "answer": proof},
        ]
    payloads.append({"token": TOKEN})

    result = None
    for i, payload in enumerate(payloads, 1):
        try:
            r = s.post(f"{BASE}/api/user/checkin", json=payload, timeout=TIMEOUT)
        except Exception as e:
            log(f"  第 {i} 次请求异常：{e}")
            continue
        try:
            js = r.json()
        except ValueError:
            js = {"code": r.status_code, "message": r.text[:200]}
        msg = str(js.get("message", ""))
        low = msg.lower()
        log(f"  第 {i} 次 → {msg or js}")
        if any(w in low for w in DENY_WORDS):
            log("  ❌ 被服务端拒绝（cookie 与 UA 不配对），停止该账号")
            return False
        if any(w in low for w in OK_WORDS) or js.get("code") == 0:
            result = js
            log(f"  ✅ 成功，字段组合 = {list(payload.keys())}")
            break

    if result is None:
        log("  ❌ 所有组合都失败，把上面日志发我")
        return False

    log("  --- 响应原文（诊断用）---")
    log("  " + json.dumps(result, ensure_ascii=False)[:700])

    try:
        pt = s.get(f"{BASE}/api/user/points", timeout=TIMEOUT).json()
        log(f"  当前积分 {pt.get('points')} | 连续签到 {pt.get('streak')}")
    except Exception:
        pass
    return True


def main():
    log("=" * 60)
    log("GLaDOS 自动签到开始")
    log("=" * 60)
    accounts = load_accounts()
    if not accounts:
        return 1
    log(f"共 {len(accounts)} 个账号")

    ok = 0
    for i, (cookie, ua) in enumerate(accounts, 1):
        try:
            if handle_account(i, cookie, ua):
                ok += 1
        except Exception as e:
            log(f"  ❌ 账号 {i} 异常：{e!r}")
        if i < len(accounts):
            time.sleep(SLEEP_BETWEEN_ACCOUNTS)

    log("=" * 60)
    log(f"完成：{ok}/{len(accounts)} 成功")
    return 0 if ok == len(accounts) else 1


if __name__ == "__&#8203;main__":
    sys.exit(main())
