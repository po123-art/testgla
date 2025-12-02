import requests
import os
from datetime import datetime

def checkin():
    url = "https://glados.network/api/user/checkin"
    headers = {
        "authorization": os.getenv("AUTH_TOKEN"),
        "content-type": "application/json",
    }
    cookies = {
        "koa:sess": os.getenv("SESSION_COOKIE"),
        "koa:sess.sig": os.getenv("SESSION_SIG")
    }
    
    response = requests.post(url, 
        headers=headers,
        cookies=cookies,
        json={"token": "glados.one"}
    )
    
    print(f"[{datetime.now()}] : {response.json()}")

if __name__ == "__main__":
    checkin()
