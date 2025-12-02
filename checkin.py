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
    
    try:

        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        

        response = requests.post(url, 
            headers=headers,
            cookies=cookies,
            json={"token": "glados.one"},
            timeout=10
        )
        

        print(response.status_code)
        
        if response.status_code == 200:

            get_status(headers, cookies)
            return True
        return False
            
    except Exception as e:
        print(f"Error: {type(e).__name__}")
        return False

def get_status(headers, cookies):
    url = "https://glados.network/api/user/status"
    
    try:
        response = requests.get(url,
            headers=headers,
            cookies=cookies,
            timeout=10
        )
        
        if response.status_code == 200:
            status = response.json()
            
            if isinstance(status, dict):
                days = status.get('days', '-')
                points = status.get('points', '-')
                expire = status.get('expireTime', '-')
                print(f"{days} {points} {expire}")
                
    except Exception:
        pass

if __name__ == "__main__":
    checkin()
