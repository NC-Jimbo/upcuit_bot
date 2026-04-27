import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# ================== 설정 ==================
WEBHOOK_URL = "https://discord.com/api/webhooks/1498362102904131594/P-9Xf0rfRswxTLO80sCdOULQUjofAzRwYDJi5MbW0z_hpUxV-2GRbpjKSuIvSQLCWAXM"
CHECK_INTERVAL = 15
RECENT_MINUTES = 25          # 여유롭게 25분
# =========================================

seen_halts = set()

def is_recent(halt_time_str: str) -> bool:
    """upcuit 시간(미국 시간)을 UTC로 변환해서 최근인지 체크"""
    try:
        # upcuit 시간 형식: "Apr 28, 01:25:43"
        halt_time = datetime.strptime(halt_time_str, "%b %d, %H:%M:%S")
        halt_time = halt_time.replace(year=datetime.now().year)
        
        # upcuit은 미국 서부 시간(PDT)일 가능성이 높음 → UTC로 변환
        halt_time = halt_time.replace(tzinfo=timezone(timedelta(hours=-7)))  # PDT = UTC-7
        
        now = datetime.now(timezone.utc)
        delta = now - halt_time
        
        return timedelta(minutes=0) <= delta <= timedelta(minutes=RECENT_MINUTES)
    except:
        return False

def send_discord_alert(halt):
    embed = {
        "title": "🚨 새로운 킷 감지! 🚨",
        "color": 0xff0000,
        "fields": [
            {"name": "종목", "value": f"{halt['symbol']} - {halt['name']}", "inline": False},
            {"name": "사유", "value": halt['reason'], "inline": False},
            {"name": "정지시간 (현지)", "value": halt['time'], "inline": True},
        ],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    
    payload = {"username": "upcuit 킷봇", "embeds": [embed]}
    requests.post(WEBHOOK_URL, json=payload, timeout=10)
    print(f"✅ 알람 전송: {halt['symbol']} | {halt['time']}")

def check_upcuit():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get("https://upcuit.com/", headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        rows = soup.select("table tbody tr")
        
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue
                
            full_text = cols[0].text.strip()
            symbol = full_text.split()[0]
            name = " ".join(full_text.split()[1:])
            reason = cols[2].text.strip()
            halt_time = cols[3].text.strip()
            
            key = f"{symbol}_{halt_time}"
            
            if key not in seen_halts and is_recent(halt_time):
                seen_halts.add(key)
                halt_data = {
                    "symbol": symbol,
                    "name": name,
                    "reason": reason,
                    "time": halt_time
                }
                send_discord_alert(halt_data)
                
    except Exception as e:
        print(f"❌ 오류: {e}")

print("🚀 upcuit 킷봇 (시간대 보정 버전) 실행 중")
print(f"→ 최근 {RECENT_MINUTES}분 이내 킷만 알람")

while True:
    check_upcuit()
    time.sleep(CHECK_INTERVAL)