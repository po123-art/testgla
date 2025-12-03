import requests
import os
from datetime import datetime

def get_user_status(headers, cookies):

    try:
        status_url = "https://glados.network/api/user/status"
        response = requests.get(status_url, headers=headers, cookies=cookies)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ 获取状态信息失败: {str(e)}")
        return None

def checkin():

    print("=" * 60)
    print(f"🕐 开始执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    

    checkin_url = "https://glados.network/api/user/checkin"
    headers = {
        "authorization": os.getenv("AUTH_TOKEN"),
        "content-type": "application/json",
    }
    cookies = {
        "koa:sess": os.getenv("SESSION_COOKIE"),
        "koa:sess.sig": os.getenv("SESSION_SIG")
    }
    
    try:
        print("\n📝 正在执行...")
        response = requests.post(checkin_url,
            headers=headers,
            cookies=cookies,
            json={"token": "glados.one"}
        )
        response.raise_for_status()
        checkin_data = response.json()
        

        print(f"\n✅ 响应: {checkin_data.get('message', 'Unknown')}")
        

        if checkin_data.get("list") and len(checkin_data["list"]) > 0:
            latest_checkin = checkin_data["list"][0]
            
            print("\n" + "=" * 60)
            print("📊 最新记录")
            print("=" * 60)
            print(f'  "business": "{latest_checkin.get("business", "N/A")}"')
            print(f'  "change": "{latest_checkin.get("change", "N/A")}"')
            print(f'  "balance": "{latest_checkin.get("balance", "N/A")}"')
            print(f'  "detail": "{latest_checkin.get("detail", "N/A")}"')
        else:
            print("\n⚠️  未找到记录")
        
        print("\n📡 正在获取状态...")
        status_data = get_user_status(headers, cookies)
        
        if status_data and status_data.get("code") == 0:
            user_data = status_data.get("data", {})
            
            print("\n" + "=" * 60)
            print("👤 状态信息")
            print("=" * 60)
            print(f'  "system_date": "{user_data.get("system_date", "N/A")}"')
            print(f'  "leftDays": "{user_data.get("leftDays", "N/A")}"')
        else:
            print("\n⚠️  获取状态失败")
        
        print("\n" + "=" * 60)
        print("✨ 流程完成")
        print("=" * 60)
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 请求失败: {str(e)}")
        raise
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    checkin()
