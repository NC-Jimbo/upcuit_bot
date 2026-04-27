import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# ================== 설정 ==================
WEBHOOK_URL = "https://discord.com/api/webhooks/1498362102904131594/P-9Xf0rfRswxTLO80sCdOULQUjofAzRwYDJi5MbW0z_hpUxV-2GRbpjKSuIvSQLCWAXM"
CHECK_INTERVAL = 15
RECENT_MINUTES = 25
# =========================================

seen_halts = set()

def is_recent(halt_time_str: str) -> bool:
    """시간 파싱 개선 + DeprecationWarning 제거"""
    try:
        halt_time = datetime.strptime(halt_time_str, "%b %d, %H:%M:%S")
        halt_time = halt_time.replace(year=datetime.now().year)
        
        # PDT (미국 서부) → KST 변환
        halt_time = halt_time.replace(tzinfo=timezone(timedelta(hours=-7)))
        halt_kst = halt_time.astimezone(timezone(timedelta(hours=9)))
        
        now_kst = datetime.now(timezone(timedelta(hours=9)))
        delta = now_kst - halt_kst
        
        return timedelta(minutes=0) <= delta <= timedelta(minutes=RECENT_MINUTES)
    except:
        return False

def send_discord_alert(halt):
    embed = {
        "title": "🚨 새로운 킷 감지! 🚨",
        "color": 0xff0000,
        "fields": [
            {"name": "📌 티커", "value": f"**{halt['symbol']}**", "inline": True},
            {"name": "🏷 종목명", "value": halt['name'], "inline": True},
            {"name": "⚠️ 사유", "value": halt['reason'], "inline": False},
            {"name": "⏰ 정지시간", "value": halt['time'], "inline": True},
        ],
        "footer": {"text": "upcuit.com • 실시간 감지"},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    
    payload = {
        "username": "upcuit 킷봇",
        "embeds": [embed]
    }
    
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

print("🚀 upcuit 킷봇 최종 버전 실행 중")
print(f"→ 최근 {RECENT_MINUTES}분 이내 알람 + DeprecationWarning 제거")

while True:
    check_upcuit()
    time.sleep(CHECK_INTERVAL)