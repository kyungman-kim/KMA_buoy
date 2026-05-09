import os
import time
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------- 설정 ----------
KMA_API_KEY = os.environ["2dzySNW3SiGc8kjVt1ohEw"]
POHANG_STN = "22106"  # ← STEP B에서 찾은 포항 부이 번호로 수정!
KST = timezone(timedelta(hours=9))

# ---------- 한글 폰트 (workflow가 NanumGothic 설치) ----------
for path in fm.findSystemFonts():
    if "NanumGothic" in path:
        fm.fontManager.addfont(path)
plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

# ---------- 기상청 API 호출 ----------
def fetch_one_hour(tm_str):
    """tm_str: 'YYYYMMDDHHMM' 형식. 해당 시각의 -59분~00분 자료 반환."""
    url = "https://apihub.kma.go.kr/api/typ01/url/sea_obs.php"
    params = {
        "tm": tm_str,
        "stn": POHANG_STN,
        "help": 0,
        "authKey": KMA_API_KEY,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.text

def parse_response(text):
    """KMA 텍스트 응답 → dict 리스트.
    컬럼 순서: TP STN_ID STN_KO TM WH WD WS WS_GST TW TA PA HM
    """
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 8:
            continue
        try:
            tm = datetime.strptime(parts[3], "%Y%m%d%H%M").replace(tzinfo=KST)
            def f(s):
                try:
                    v = float(s)
                    return None if v <= -9 else v   # 결측치 처리
                except Exception:
                    return None
            out.append({
                "tm": tm,
                "wh": f(parts[4]),
                "wd": f(parts[5]),
                "ws": f(parts[6]),
            })
        except Exception as e:
            print(f"parse skip: {line[:80]} ({e})")
    return out

def fetch_24h():
    """현재 시각 기준 과거 24시간 정시 데이터 수집."""
    now = datetime.now(KST).replace(minute=0, second=0, microsecond=0)
    rows = []
    for h in range(24, -1, -1):
        t = now - timedelta(hours=h)
        tm_str = t.strftime("%Y%m%d%H%M")
        try:
            text = fetch_one_hour(tm_str)
            r = parse_response(text)
            rows.extend(r)
            print(f"{tm_str}: {len(r)} rows")
        except Exception as e:
            print(f"{tm_str}: FAIL - {e}")
        time.sleep(0.3)  # 서버 배려
    # 중복 제거 + 시간순 정렬
    seen = set()
    uniq = []
    for r in sorted(rows, key=lambda x: x["tm"]):
        if r["tm"] not in seen:
            seen.add(r["tm"])
            uniq.append(r)
    return uniq

# ---------- 그래프 ----------
def make_plot(rows, out_path):
    times = [r["tm"] for r in rows]
    ws = [r["ws"] for r in rows]
    wd = [r["wd"] for r in rows]
    wh = [r["wh"] for r in rows]

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(times, ws, marker="o")
    axes[0].set_ylabel("풍속 (m/s)")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(times, wd, marker="o", color="orange")
    axes[1].set_ylabel("풍향 (°)"); axes[1].set_ylim(0, 360)
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(times, wh, marker="o", color="navy")
    axes[2].set_ylabel("유의파고 (m)")
    axes[2].grid(True, alpha=0.3)

    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H시"))
    fig.autofmt_xdate()
    fig.suptitle(f"포항 해양기상부이  ·  {datetime.now(KST):%Y-%m-%d %H:%M KST}",
                 fontsize=14)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)

# ---------- main ----------
if __name__ == "__main__":
    Path("plots").mkdir(exist_ok=True)
    rows = fetch_24h()
    print(f"\nTotal collected: {len(rows)} rows")
    if not rows:
        raise SystemExit("No data fetched — 키나 지점번호를 확인하세요")
    make_plot(rows, "plots/latest.png")
    print("Saved plots/latest.png")
