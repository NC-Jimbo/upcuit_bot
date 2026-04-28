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

# ================== 장 시간 체크 함수 ==================
def is_market_open() -> bool:
    """한국 시간 기준으로 미국 정규장(EDT)인지 확인"""
    now_kst = datetime.now(timezone(timedelta(hours=9)))
    weekday = now_kst.weekday()  # 0=월요일 ~ 6=일요일
    hour = now_kst.hour
    minute = now_kst.minute

    # 주말 제외
    if weekday >= 5:  # 토요일, 일요일
        return False

    # 미국 정규장 시간 (현재 DST 기간: KST 기준 22:30 ~ 05:00)
    # 22:30 ~ 24:00 또는 00:00 ~ 05:00
    if (hour == 22 and minute >= 30) or (hour >= 23) or (0 <= hour <= 4) or (hour == 5 and minute <= 0):
        return True
    return False

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
                
            # --- 1. 티커와 종목명 분리 로직 강화 ---
            # 첫 번째 칸(cols[0])에서 텍스트를 가져와 공백으로 나눕니다.
            raw_text = cols[0].get_text(separator=" ", strip=True).split()
            
            if not raw_text:
                continue

            symbol = raw_text[0].upper()  # 첫 단어는 무조건 티커 (대문자 변환)
            name = " ".join(raw_text[1:]) # 나머지는 모두 종목명
            
            # 만약 종목명이 비어있다면 "N/A" 처리
            if not name:
                name = "-"

            reason = cols[2].get_text(strip=True)
            halt_time = cols[3].get_text(strip=True)
            
            # --- 2. 중복 방지 키 생성 (공백 제거) ---
            # 시간과 티커를 조합해 고유 키 생성
            key = f"{symbol}_{halt_time}".replace(" ", "")
            
            if key not in seen_halts:
                # 최근 발생한 알람인지 확인
                if is_recent(halt_time):
                    # 중요: 알람 전송 전 세트에 먼저 추가해서 중복 진입 차단
                    seen_halts.add(key)
                    
                    halt_data = {
                        "symbol": symbol,
                        "name": name,
                        "reason": reason,
                        "time": halt_time
                    }
                    send_discord_alert(halt_data)
                else:
                    # 너무 오래된 기록이면 세트에만 넣고 무시
                    seen_halts.add(key)
                
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

print("🚀 upcuit 킷봇 최종 버전 실행 중")
print(f"→ 최근 {RECENT_MINUTES}분 이내 알람 + DeprecationWarning 제거")

while True:
    now = datetime.now(timezone(timedelta(hours=9)))   # 한국 시간
    hour = now.hour
    weekday = now.weekday()

    # 미국 정규장 시간 (한국 시간 기준, DST 적용)
    is_regular_market = (
        weekday < 5 and                                      # 주말 제외
        ((hour == 22 and now.minute >= 30) or                # 22:30 ~
         (23 <= hour <= 23) or 
         (0 <= hour <= 4) or 
         (hour == 5 and now.minute <= 0))                     # ~ 05:00
    )

    if not is_regular_market:
        print(f"📴 [{now.strftime('%m-%d %H:%M')}] 미국 장 마감 / 주말입니다. 1시간 후 다시 체크...")
        time.sleep(3600)          # ← 1시간 동안 완전 sleep (CPU 거의 안 씀)
        continue

    # 정규장일 때만 실행
    check_upcuit()
    time.sleep(CHECK_INTERVAL)