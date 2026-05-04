import requests
from datetime import datetime, timezone, timedelta

WEBHOOK_URL = "https://discord.com/api/webhooks/1498362102904131594/P-9Xf0rfRswxTLO80sCdOULQUjofAzRwYDJi5MbW0z_hpUxV-2GRbpjKSuIvSQLCWAXM"

def test_webhook():
    embed = {
        "title": "🔥 웹훅 테스트",
        "description": "봇이 정상적으로 웹훅을 보내고 있습니다.\n테스트 시간: " + datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S"),
        "color": 0x00ff00,
        "footer": {"text": "upcuit 킷봇 테스트"}
    }

    payload = {
        "username": "upcuit 킷봇",
        "embeds": [embed]
    }

    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if r.status_code == 204:
            print("✅ 웹훅 전송 성공! (Discord에 메시지 와야 함)")
        else:
            print(f"❌ 웹훅 실패: {r.status_code} {r.text}")
    except Exception as e:
        print(f"❌ 요청 오류: {e}")

print("웹훅 테스트 시작...")
test_webhook()