import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

WEBHOOK_URL = "https://discord.com/api/webhooks/1498362102904131594/P-9Xf0rfRswxTLO80sCdOULQUjofAzRwYDJi5MbW0z_hpUxV-2GRbpjKSuIvSQLCWAXM"
CHECK_INTERVAL = 20          # 20초마다 체크
RECENT_MINUTES_AT_START = 15 # 시작할 때만 15분 필터 적용

seen_halts = set()
bot_start_time = datetime.now(timezone(timedelta(hours=9)))

def is_market_open() -> bool:
    now = datetime.now(timezone(timedelta(hours=9)))
    if now.weekday() >= 5:
        return False
    h, m = now.hour, now.minute
    return (h == 22 and m >= 30) or (23 <= h) or (0 <= h <= 5)

def is_recent_at_start(halt_time_str: str) -> bool:
    """봇 시작할 때만 쓰는 15분 필터"""
    try:
        dt = datetime.strptime(halt_time_str, "%b %d, %H:%M:%S")
        dt = dt.replace(year=datetime.now().year)
        dt = dt.replace(tzinfo=timezone(timedelta(hours=-4)))
        dt_kst = dt.astimezone(timezone(timedelta(hours=9)))
        
        if dt_kst > datetime.now(timezone(timedelta(hours=9))):
            dt_kst -= timedelta(days=1)
            
        minutes_ago = (datetime.now(timezone(timedelta(hours=9))) - dt_kst).total_seconds() / 60
        return minutes_ago <= RECENT_MINUTES_AT_START
    except:
        return False

def send_alert(halt):
    embed = {
        "title": "🚨 실시간 킷 감지 🚨",
        "color": 0xff0000,
        "fields": [
            {"name": "🔥 티커", "value": f"**{halt['symbol']}**", "inline": True},
            {"name": "📛 종목명", "value": halt['name'], "inline": True},
            {"name": "⚠️ 사유", "value": halt['reason'], "inline": False},
            {"name": "⏰ 정지 시간", "value": halt['time'], "inline": True},
            {"name": "🕒 감지 시간", "value": datetime.now(timezone(timedelta(hours=9))).strftime("%H:%M:%S"), "inline": True},
        ],
        "footer": {"text": "upcuit.com • 킷봇"},
        "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat()
    }
    
    payload = {
        "username": "upcuit 킷봇",
        "embeds": [embed]
    }
    
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"✅ 전송 완료 → {halt['symbol']}")
    except:
        print("❌ 웹훅 전송 실패")

def check_upcuit():
    try:
        r = requests.get("https://upcuit.com/", 
                        headers={"User-Agent": "Mozilla/5.0"}, 
                        timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        new_count = 0
        for row in soup.select("table tbody tr"):
            cols = row.find_all("td")
            if len(cols) < 4: continue

            raw = cols[0].get_text(separator=" ", strip=True).split()
            if not raw: continue
                
            symbol = raw[0].upper()
            name = " ".join(raw[1:]) if len(raw) > 1 else "-"
            reason = cols[2].get_text(strip=True)
            halt_time = cols[3].get_text(strip=True)

            key = f"{symbol}_{halt_time}".replace(" ", "")

            if key not in seen_halts:
                seen_halts.add(key)
                
                # 시작 직후에는 15분 필터 적용, 이후에는 무조건 새로 올라온 것 보내기
                if (datetime.now(timezone(timedelta(hours=9))) - bot_start_time).total_seconds() < 300:  # 시작 5분 이내
                    if is_recent_at_start(halt_time):
                        send_alert({"symbol": symbol, "name": name, "reason": reason, "time": halt_time})
                        new_count += 1
                else:
                    # 시작 5분 이후부터는 새로 생긴 건 무조건 전송
                    send_alert({"symbol": symbol, "name": name, "reason": reason, "time": halt_time})
                    new_count += 1

        if new_count == 0:
            print("   📭 새 킷 없음")
        else:
            print(f"   🔥 {new_count}개 전송")
            
    except Exception as e:
        print(f"❌ 크롤링 오류: {e}")


# ================== 실행 ==================
print("🚀 upcuit 킷봇 실행 중 (새로 올라오는 것만 전송)")
print(f"→ 시작 후 15분 이내 필터 + 이후 신규 킷만 감지")

while True:
    if is_market_open():
        print(f"🟢 [{datetime.now(timezone(timedelta(hours=9))).strftime('%m-%d %H:%M:%S')}] 체크 중...")
        check_upcuit()
        time.sleep(CHECK_INTERVAL)
    else:
        print(f"📴 장 마감 - 1시간 대기")
        time.sleep(3600)