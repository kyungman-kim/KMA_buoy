import os
import time
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------- 설정 ----------
KMA_API_KEY = os.environ["KMA_API_KEY"]
POHANG_STN = "22106"
KST = timezone(timedelta(hours=9))
HOURS_BACK = 72   # 72시간

# ---------- 한글 폰트 ----------
for path in fm.findSystemFonts():
    if "NanumGothic" in path:
        fm.fontManager.addfont(path)
plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False


def fetch_one_hour(tm_str):
    """kma_buoy.php: 풍향/풍속/파고/파주기/파향까지 모두 제공"""
    url = "https://apihub.kma.go.kr/api/typ01/url/kma_buoy.php"
    params = {"tm": tm_str, "stn": POHANG_STN, "help": 0, "authKey": KMA_API_KEY}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.text


def parse_response(text):
    """
    kma_buoy.php 응답 (공백 구분, 17개 컬럼):
    [0]TM [1]STN [2]WD1 [3]WS1 [4]WS1_GST [5]WD2 [6]WS2 [7]WS2_GST
    [8]PA [9]HM [10]TA [11]TW [12]WH_MAX [13]WH_SIG [14]WH_AVE [15]WP [16]WO
    """
    out = []
    debug = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not debug:
            print(f"DEBUG cols({len(parts)}): {parts}")
            debug = True
        if len(parts) < 17:
            continue
        try:
            tm = datetime.strptime(parts[0], "%Y%m%d%H%M").replace(tzinfo=KST)

            def f(s):
                try:
                    v = float(s)
                    return None if v <= -9 else v
                except Exception:
                    return None

            out.append({
                "tm": tm,
                "wd": f(parts[2]),    # 풍향 WD1
                "ws": f(parts[3]),    # 풍속 WS1
                "wh": f(parts[13]),   # 유의파고 WH_SIG
                "wp": f(parts[15]),   # 파주기 WP
                "wo": f(parts[16]),   # 파향 WO
            })
        except Exception as e:
            print(f"parse skip: {line[:100]} ({e})")
    return out


def fetch_period():
    now = datetime.now(KST).replace(minute=0, second=0, microsecond=0)
    rows = []
    for h in range(HOURS_BACK, -1, -1):
        t = now - timedelta(hours=h)
        tm_str = t.strftime("%Y%m%d%H%M")
        try:
            text = fetch_one_hour(tm_str)
            r = parse_response(text)
            rows.extend(r)
            if h % 12 == 0:
                print(f"{tm_str}: {len(r)} rows")
        except Exception as e:
            print(f"{tm_str}: FAIL - {e}")
        time.sleep(0.2)
    seen = set()
    uniq = []
    for r in sorted(rows, key=lambda x: x["tm"]):
        if r["tm"] not in seen:
            seen.add(r["tm"])
            uniq.append(r)
    return uniq


def plot_direction_circles(ax, times, dirs, label, color="black"):
    """방향(degree)을 원형 심볼로 표시. y축 0~360°, 90° 틱."""
    valid = [(t, d) for t, d in zip(times, dirs) if d is not None]
    ax.set_ylim(0, 360)
    ax.set_yticks([0, 90, 180, 270, 360])
    ax.set_ylabel(label + " (°)")
    ax.grid(True, alpha=0.3)
    if not valid:
        ax.text(0.5, 0.5, "데이터 없음", transform=ax.transAxes, ha="center")
        return
    vt = [x[0] for x in valid]
    vd = [x[1] for x in valid]
    ax.scatter(vt, vd, s=25, color=color, marker="o", alpha=0.8)


def make_plot(rows, out_path):
    times = [r["tm"] for r in rows]
    ws = [r["ws"] for r in rows]
    wd = [r["wd"] for r in rows]
    wh = [r["wh"] for r in rows]
    wo = [r["wo"] for r in rows]

    fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

    axes[0].plot(times, ws, marker="o", color="tab:blue", markersize=3)
    axes[0].set_ylabel("풍속 (m/s)")
    axes[0].grid(True, alpha=0.3)

    plot_direction_circles(axes[1], times, wd, "풍향", color="tab:blue")

    axes[2].plot(times, wh, marker="o", color="navy", markersize=3)
    axes[2].set_ylabel("유의파고 (m)")
    axes[2].grid(True, alpha=0.3)

    plot_direction_circles(axes[3], times, wo, "파향", color="navy")

    axes[3].xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H시"))
    axes[3].xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 6, 12, 18]))
    fig.autofmt_xdate()
    fig.suptitle(
        f"포항 해양기상부이 · 최근 {HOURS_BACK}시간  "
        f"(생성: {datetime.now(KST):%Y-%m-%d %H:%M KST})",
        fontsize=14,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    Path("plots").mkdir(exist_ok=True)
    rows = fetch_period()
    print(f"\nTotal collected: {len(rows)} rows")
    if not rows:
        raise SystemExit("No data fetched")
    make_plot(rows, "plots/latest.png")
    print("Saved plots/latest.png")
