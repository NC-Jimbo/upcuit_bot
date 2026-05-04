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

# ================== 장 시간 체크 ==================
def is_market_open() -> bool:
    """한국시간(KST) 기준 미국 정규장 여부"""
    now_kst = datetime.now(timezone(timedelta(hours=9)))
    weekday = now_kst.weekday()
    hour = now_kst.hour
    minute = now_kst.minute

    if weekday >= 5:  # 토, 일
        return False

    # 미국 장: KST 기준 22:30 ~ 다음날 05:00 (DST 적용)
    if (hour == 22 and minute >= 30) or (23 <= hour <= 23) or (0 <= hour <= 5):
        return True
    return False


def is_recent(halt_time_str: str) -> bool:
    """upcuit 시간 파싱 + EDT → KST 변환"""
    try:
        # 예: "May 04, 21:45:12"
        halt_time = datetime.strptime(halt_time_str, "%b %d, %H:%M:%S")
        halt_time = halt_time.replace(year=datetime.now().year)
        
        # EDT (UTC-4) 적용
        halt_time = halt_time.replace(tzinfo=timezone(timedelta(hours=-4)))
        halt_kst = halt_time.astimezone(timezone(timedelta(hours=9)))
        
        now_kst = datetime.now(timezone(timedelta(hours=9)))
        delta = now_kst - halt_kst
        
        return timedelta(minutes=0) <= delta <= timedelta(minutes=RECENT_MINUTES)
    except Exception as e:
        print(f"⏰ 시간 파싱 실패: {halt_time_str} → {e}")
        return False


def send_discord_alert(halt):
    """디스코드 웹훅 전송"""
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
        "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat()
    }
    
    payload = {
        "username": "upcuit 킷봇",
        "embeds": [embed]
    }
    
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"✅ 웹훅 전송 성공: {halt['symbol']} | Status: {r.status_code}")
    except Exception as e:
        print(f"❌ 웹훅 전송 실패: {e}")


def check_upcuit():
    """upcuit.com 크롤링"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get("https://upcuit.com/", headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("table tbody tr")
        
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue

            # 티커 + 종목명 분리
            raw_text = cols[0].get_text(separator=" ", strip=True).split()
            if not raw_text:
                continue
                
            symbol = raw_text[0].upper()
            name = " ".join(raw_text[1:]) if len(raw_text) > 1 else "-"
            
            reason = cols[2].get_text(strip=True)
            halt_time = cols[3].get_text(strip=True)
            
            # 디버깅용 출력
            print(f"발견 → {symbol} | {halt_time} | 최근? {is_recent(halt_time)}")
            
            # 중복 체크 키
            key = f"{symbol}_{halt_time}".replace(" ", "")
            
            if key not in seen_halts:
                if is_recent(halt_time):
                    seen_halts.add(key)
                    halt_data = {
                        "symbol": symbol,
                        "name": name,
                        "reason": reason,
                        "time": halt_time
                    }
                    send_discord_alert(halt_data)
                else:
                    seen_halts.add(key)  # 오래된 건 기록만
                
    except Exception as e:
        print(f"❌ 크롤링 오류: {e}")


# ================== 메인 루프 ==================
print("🚀 upcuit 킷봇 최종 버전 실행 중")
print(f"→ 최근 {RECENT_MINUTES}분 이내 알람 + 타임존 수정 완료")

while True:
    now = datetime.now(timezone(timedelta(hours=9)))
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute

    is_regular_market = (
        weekday < 5 and
        ((hour == 22 and minute >= 30) or (23 <= hour <= 23) or (0 <= hour <= 5))
    )

    if not is_regular_market:
        print(f"📴 [{now.strftime('%m-%d %H:%M')}] 미국 장 마감 / 주말입니다. 1시간 후 다시 체크...")
        time.sleep(3600)
        continue

    # 장 중일 때
    print(f"🟢 [{now.strftime('%m-%d %H:%M:%S')}] 미국 장 운영 중 → 체크 중...")
    check_upcuit()
    time.sleep(CHECK_INTERVAL)