import os
import time
import requests
import numpy as np
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


def plot_direction_arrows(ax, times, dirs, label, color="black"):
    """
    방향(degree, 'from' 기준)을 화살표 심볼로 표시.
    화살표는 '바람·파도가 가는 방향'으로 향함.
    """
    valid = [(t, d) for t, d in zip(times, dirs) if d is not None]
    if not valid:
        ax.text(0.5, 0.5, "데이터 없음", transform=ax.transAxes, ha="center")
        ax.set_yticks([])
        ax.set_ylabel(label)
        return
    vt = [x[0] for x in valid]
    vd = np.array([x[1] for x in valid], dtype=float)
    rad = np.deg2rad(vd)
    u = -np.sin(rad)   # '~로부터'의 반대 방향 = 진행 방향
    v = -np.cos(rad)
    ax.quiver(vt, np.zeros(len(vt)), u, v,
              angles="uv", scale_units="inches", scale=5,
              width=0.004, color=color, pivot="mid")
    ax.set_ylim(-1, 1)
    ax.set_yticks([])
    ax.set_ylabel(label)
    ax.axhline(0, color="gray", linewidth=0.3, alpha=0.5)


def make_plot(rows, out_path):
    times = [r["tm"] for r in rows]
    ws = [r["ws"] for r in rows]
    wd = [r["wd"] for r in rows]
    wh = [r["wh"] for r in rows]
    wo = [r["wo"] for r in rows]

    fig, axes = plt.subplots(
        4, 1, figsize=(12, 9), sharex=True,
        gridspec_kw={"height_ratios": [3, 1, 3, 1]},
    )

    axes[0].plot(times, ws, marker="o", color="tab:blue", markersize=3)
    axes[0].set_ylabel("풍속 (m/s)")
    axes[0].grid(True, alpha=0.3)

    plot_direction_arrows(axes[1], times, wd, "풍향", color="tab:blue")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(times, wh, marker="o", color="navy", markersize=3)
    axes[2].set_ylabel("유의파고 (m)")
    axes[2].grid(True, alpha=0.3)

    plot_direction_arrows(axes[3], times, wo, "파향", color="navy")
    axes[3].grid(True, alpha=0.3)

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
