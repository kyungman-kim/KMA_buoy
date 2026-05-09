import os
import json
import time
import requests
from datetime import datetime, timezone, timedelta

KAKAO_REST_API_KEY = os.environ["KAKAO_REST_API_KEY"]
KAKAO_CLIENT_SECRET = os.environ["KAKAO_CLIENT_SECRET"]
KAKAO_REFRESH_TOKEN = os.environ["KAKAO_REFRESH_TOKEN"]
GITHUB_REPO = os.environ["GITHUB_REPOSITORY"]
KST = timezone(timedelta(hours=9))

# GitHub Pages 뷰어 URL (본인 저장소에 맞게 수정)
VIEWER_URL = "https://kyungman-kim.github.io/KMA_buoy/"


def refresh_access_token():
    r = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": KAKAO_REST_API_KEY,
            "client_secret": KAKAO_CLIENT_SECRET,
            "refresh_token": KAKAO_REFRESH_TOKEN,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def wait_for_image(url, max_attempts=20, interval=5):
    """raw URL이 실제로 접근 가능해질 때까지 대기 (최대 ~100초)."""
    for i in range(max_attempts):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200 and len(r.content) > 1000:
                print(f"✓ Image ready after {i*interval}s, size={len(r.content)} bytes")
                return True
            print(f"  attempt {i+1}: status={r.status_code}, size={len(r.content)}")
        except Exception as e:
            print(f"  attempt {i+1}: {e}")
        time.sleep(interval)
    return False


def send_to_self(image_url, link_url):
    access_token = refresh_access_token()
    template = {
        "object_type": "feed",
        "content": {
            "title": f"포항 부이 일일보고 ({datetime.now(KST):%m-%d %H:%M})",
            "description": "최근 72시간 바람·파랑 시계열 (탭하여 확대)",
            "image_url": image_url,
            "image_width": 1600,
            "image_height": 900,
            "link": {
                "web_url": link_url,
                "mobile_web_url": link_url,
            },
        },
    }
    r = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template)},
        timeout=30,
    )
    r.raise_for_status()
    print("Kakao OK:", r.json())


if __name__ == "__main__":
    ts = int(datetime.now().timestamp())
    image_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/plots/latest.png?t={ts}"
    print(f"Image URL : {image_url}")
    print(f"Viewer URL: {VIEWER_URL}")
    if not wait_for_image(image_url):
        raise SystemExit("Image URL not accessible")
    send_to_self(image_url, VIEWER_URL)
