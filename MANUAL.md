# 포항 해양기상부이 카톡 자동 전송 봇 — 구축 매뉴얼

매일 정해진 시각에 기상청 API에서 포항 해양기상부이의 72시간 자료를 가져와 시계열 그래프를 그리고, 본인 카카오톡 ("나와의 채팅") 으로 자동 전송하는 봇을 GitHub Actions로 구축하는 방법.

---

## 동작 흐름

```
[매일 한국시간 오전 8시]
        ↓
GitHub Actions 자동 실행
        ↓
기상청 API허브 호출 (72시간치 데이터)
        ↓
matplotlib 그래프 생성 (풍속·풍향·유의파고·파향)
        ↓
저장소에 plots/latest.png 커밋
        ↓
카카오톡 "나에게 보내기" 로 전송
```

## 사전 준비

- GitHub 계정 (없으면 [github.com](https://github.com)에서 가입)
- 카카오 계정 (평소 카톡 쓰시는 그 계정)
- 작업 시간: 1~2시간 (처음이면 2~3시간)

## 비용

전부 무료. GitHub Actions Public 저장소는 무제한 무료, 카카오 메시지 API도 본인에게 보내기는 무료.

---

# Phase A. GitHub 저장소 만들기

## A-1. 저장소 생성

1. GitHub 로그인 후 좌측 상단 **+** → **New repository**
2. 입력:
   - Repository name: `KMA_buoy` (자유)
   - **Public** 선택 (⚠️ Private이면 카톡으로 이미지 못 보냅니다)
   - **Add a README file** 체크
3. **Create repository**

> API 키 같은 비밀 정보는 코드가 아니라 **Settings → Secrets** 에 들어가므로, Public이어도 노출되지 않습니다.

## A-2. 워크플로우 폴더 만들기

저장소 메인 → **Add file → Create new file** → 파일명 입력란에 다음을 정확히 입력:

```
.github/workflows/daily.yml
```

(슬래시를 직접 타이핑하면 GitHub이 자동으로 폴더를 만들어줍니다.)

내용은 일단 비워두고 Phase F에서 채울 거예요. 또는 임시로 다음 한 줄만 넣고 Commit:

```yaml
name: placeholder
```

---

# Phase B. 기상청 API 키 받기 (기상청 API허브)

⚠️ 공공데이터포털(data.go.kr)의 해양 API는 공공기관 한정이라 개인은 안 됩니다. **기상청 API허브 (apihub.kma.go.kr)** 를 써야 합니다.

## B-1. 가입

1. [apihub.kma.go.kr](https://apihub.kma.go.kr) 접속
2. 우측 상단 **회원가입** → **개인회원** 선택 (기관회원은 공문 필요)
3. 이메일 인증 완료

## B-2. API 활용 신청

1. 로그인 후 좌측 메뉴 **해양관측** → **해양기상부이·파고부이관측**
2. 우측 상단 **활용신청** 버튼
3. 활용목적: "개인 학습 / 일일 모니터링" 등 자유롭게 작성
4. 보통 즉시 승인됨

## B-3. 인증키 복사

1. 우측 상단 **마이페이지** → **API인증키 관리**
2. 발급된 인증키(authKey) 값을 복사 → 메모장에 백업

> ⚠️ 발급 직후 1시간 정도는 키가 활성화 안 될 수 있습니다. 호출이 실패하면 잠시 후 재시도.

## B-4. 포항 부이 지점번호 확인

브라우저 주소창에 다음 입력 (`{KEY}` 자리에 본인 키):

```
https://apihub.kma.go.kr/api/typ01/url/sea_obs.php?tm=202405081200&stn=0&help=1&authKey={KEY}
```

응답에서 "포항"을 Ctrl+F로 찾기. 보통 **22106** 입니다.

---

# Phase C. 카카오 개발자 앱 만들기

⚠️ 가장 까다로운 부분입니다. 천천히 따라하세요.

## C-1. 가입 + 앱 생성

1. [developers.kakao.com](https://developers.kakao.com) → 카카오 계정으로 로그인 (자동 가입됨)
2. 상단 메뉴 **앱** → **애플리케이션 추가하기**
3. 입력:
   - 앱 이름: 자유 (예: `포항부이봇`)
   - 사업자명/회사명: 본인 이름
   - 앱 대표 도메인: `github.com` (실제 안 써도 됨)
4. **저장**

## C-2. ⚠️ REST API 키 "추가" (핵심)

기본으로 생성된 "Default Rest API Key"는 OAuth에 사용 못 합니다 (Redirect URI 미등록). **새 REST API 키를 추가**해야 합니다.

1. 만든 앱 클릭 → 좌측 사이드바 **앱** 메뉴 펼치기 (∨ 클릭)
2. **플랫폼 키** 클릭
3. 우측 **REST API 키 추가** 버튼 클릭
4. 입력:
   - 키 이름: `buoy-bot` (자유)
   - 호출 허용 IP 주소: **비워둠**
   - **카카오 로그인 리다이렉트 URI**: `https://example.com/oauth` (정확히 이 값)
5. **저장**

저장 후 새 REST API 키와 함께 **Client Secret** 이 자동 생성됩니다.

## C-3. 키 값 메모

플랫폼 키 페이지에 두 개의 키가 보일 거예요:
- Default Rest API Key (대표) — **사용 안 함**
- buoy-bot — **이걸 사용**

다음 두 값을 메모장에 백업:
- buoy-bot의 **REST API 키 값** (32자 영숫자)
- buoy-bot의 **Client Secret 값** (👁 눈 모양 클릭해서 확인)

## C-4. 카카오 로그인 활성화

1. 좌측 사이드바 **제품 설정 → 카카오 로그인** 클릭
2. **사용 설정** 토글을 **ON** (파란색으로 변함)

## C-5. 메시지 전송 권한 활성화

1. 좌측 사이드바 **카카오 로그인 → 동의항목** (또는 접근권한)
2. **카카오톡 메시지 전송 (talk_message)** 행의 우측 **설정** 클릭
3. **선택 동의**로 설정 → 사유 적당히 작성 → 저장
4. 상태가 **"사용함"** 으로 바뀌어야 함

---

# Phase D. 카카오 OAuth 토큰 받기 (수동, 한 번만)

이 단계는 한 번만 하면 됩니다. 약 2개월 후 refresh_token이 만료되면 다시 한 번 더.

## D-1. 인증 코드 받기 (브라우저)

다음 URL의 `{KEY}` 자리에 **buoy-bot의 REST API 키** 입력 후 브라우저 주소창에 입력:

```
https://kauth.kakao.com/oauth/authorize?response_type=code&client_id={KEY}&redirect_uri=https://example.com/oauth&scope=talk_message
```

진행:
1. 카카오 로그인
2. **동의하기** 클릭
3. `https://example.com/oauth?code=XXXXXXXX...` 같은 주소로 이동
4. 페이지가 에러 나도 무시 — **주소창의 `code=` 뒤 문자열 전체를 복사**

⏱️ 이 코드는 **10분 안에 다음 단계까지** 완료해야 합니다.

## D-2. 리프레시 토큰 받기 (GitHub Codespaces)

PC에 아무것도 설치하지 않고 브라우저에서 명령어를 실행할 수 있습니다.

1. 본인 저장소 페이지로 이동
2. 우측 상단 초록색 **`<> Code`** → 상단 탭 **Codespaces** → **Create codespace on main**
3. 30초~1분 대기 후 VSCode 비슷한 화면 열림
4. 화면 아래쪽 **터미널** 영역 클릭

다음 한 줄을 통째로 복사하되 **세 군데를 본인 값으로 교체**한 뒤 터미널에 붙여넣기 (Ctrl+V) → Enter:

```bash
curl -X POST "https://kauth.kakao.com/oauth/token" -d "grant_type=authorization_code" -d "client_id=REST_API_키" -d "client_secret=Client_Secret_값" -d "redirect_uri=https://example.com/oauth" -d "code=방금복사한_code"
```

성공 응답 (JSON):

```json
{
  "access_token": "...",
  "refresh_token": "긴_문자열_이게_핵심",
  "expires_in": 21599,
  "scope": "talk_message",
  "refresh_token_expires_in": 5183999
}
```

`refresh_token` 값을 **메모장에 백업**.

---

# Phase E. GitHub Secrets에 키 등록

저장소 → **Settings → Secrets and variables → Actions → New repository secret**

총 4개 등록:

| Name | Value |
|---|---|
| `KMA_API_KEY` | Phase B에서 받은 기상청 인증키 |
| `KAKAO_REST_API_KEY` | buoy-bot의 REST API 키 |
| `KAKAO_CLIENT_SECRET` | buoy-bot의 Client Secret |
| `KAKAO_REFRESH_TOKEN` | Phase D-2에서 받은 refresh_token |

---

# Phase F. 코드 파일 추가

저장소에 다음 4개 파일을 추가합니다. 모두 **Add file → Create new file** 로 만들 수 있어요.

## F-1. `requirements.txt`

```
requests
matplotlib
```

## F-2. `main.py`

```python
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
    """kma_buoy.php: 풍향/풍속/파고/파주기/파향 모두 제공"""
    url = "https://apihub.kma.go.kr/api/typ01/url/kma_buoy.php"
    params = {"tm": tm_str, "stn": POHANG_STN, "help": 0, "authKey": KMA_API_KEY}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.text


def parse_response(text):
    """
    응답 형식 (공백 구분, 17개 컬럼):
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
                "wd": f(parts[2]),    # 풍향
                "ws": f(parts[3]),    # 풍속
                "wh": f(parts[13]),   # 유의파고
                "wp": f(parts[15]),   # 파주기
                "wo": f(parts[16]),   # 파향
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

    fig, axes = plt.subplots(4, 1, figsize=(16, 9), sharex=True)

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
```

## F-3. `send_kakao.py`

```python
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


def send_to_self(image_url):
    access_token = refresh_access_token()
    template = {
        "object_type": "feed",
        "content": {
            "title": f"포항 부이 일일보고 ({datetime.now(KST):%m-%d %H:%M})",
            "description": "최근 72시간 바람·파랑 시계열",
            "image_url": image_url,
            "image_width": 1600,
            "image_height": 900,
            "link": {
                "web_url": image_url,
                "mobile_web_url": image_url,
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
    print(f"Image URL: {image_url}")
    if not wait_for_image(image_url):
        raise SystemExit("Image URL not accessible")
    send_to_self(image_url)
```

## F-4. `.github/workflows/daily.yml`

```yaml
name: Daily Buoy Bot

on:
  schedule:
    - cron: '0 23 * * *'   # 한국시간 오전 8시 (UTC 23:00)
  workflow_dispatch:

permissions:
  contents: write

jobs:
  run-bot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Korean fonts
        run: |
          sudo apt-get update
          sudo apt-get install -y fonts-nanum
          fc-cache -f

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install -r requirements.txt

      - name: Generate plot
        run: python main.py
        env:
          KMA_API_KEY: ${{ secrets.KMA_API_KEY }}

      - name: Commit plot
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add plots/
          git diff --cached --quiet || git commit -m "Update plot $(date -u +%Y-%m-%d_%H%M)"
          git push

      - name: Send Kakao
        run: python send_kakao.py
        env:
          KAKAO_REST_API_KEY: ${{ secrets.KAKAO_REST_API_KEY }}
          KAKAO_CLIENT_SECRET: ${{ secrets.KAKAO_CLIENT_SECRET }}
          KAKAO_REFRESH_TOKEN: ${{ secrets.KAKAO_REFRESH_TOKEN }}
```

⚠️ 단계 순서가 핵심: **그림 생성 → 저장소에 commit → 그제서야 카톡 전송** (카카오 서버가 raw URL로 그림을 가져갈 수 있도록).

---

# Phase G. 실행 및 확인

## G-1. 수동 실행

1. 저장소 → **Actions** 탭
2. 좌측에서 **Daily Buoy Bot** 클릭
3. 우측 **Run workflow** → **Run workflow** 클릭
4. 1~3분 대기

## G-2. 결과 확인

- ✅ **저장소 메인** 의 `plots/latest.png` → 그림 생성됨
- ✅ **카카오톡 "나와의 채팅"** → 그림 카드 메시지 도착

## G-3. 자동 실행 시간 변경

`daily.yml` 의 `cron: '0 23 * * *'` 부분 수정.
- 형식: `분 시 일 월 요일` (UTC 기준)
- 한국시간 오전 8시 = UTC 23:00 (전날) → `0 23 * * *`
- 한국시간 오후 7시 = UTC 10:00 → `0 10 * * *`

---

# 자주 겪는 에러 / 트러블슈팅

## "Invalid workflow file" / yaml syntax error

복사 붙여넣기 중 첫 글자나 들여쓰기가 깨졌을 가능성. workflow YAML을 정확히 다시 붙여넣기.

## KOE004: 앱 관리자 설정 오류

카카오 OAuth 인증 URL 접속 시.

원인:
- buoy-bot REST API 키에 Redirect URI가 등록 안 됨
- 또는 카카오 로그인이 비활성화됨

해결: Phase C-2 (Redirect URI 등록), C-4 (카카오 로그인 ON) 다시 확인.

## KOE010: Bad client credentials

curl 명령어에서.

원인 1: client_id가 잘못됨
- "Default Rest API Key"가 아닌 "buoy-bot"의 REST API 키를 써야 함

원인 2: client_secret 누락
- buoy-bot 키는 client_secret도 함께 요구함. curl에 `-d "client_secret=..."` 빠뜨리지 말 것.

## KOE320: invalid_grant

curl 명령어에서.

원인: 인증 code가 만료됨 (10분 초과 또는 한 번 사용됨).

해결: Phase D-1부터 다시 (인증 URL 새로 열어서 새 code 받기).

## "Process completed with exit code 1" (워크플로우)

GitHub Actions 로그를 위로 스크롤하면 진짜 에러가 있음.

흔한 원인:
- `os.environ["KEY_NAME"]` 의 KEY_NAME 자리에 실제 값을 적었음 (이름이어야 함)
- Secrets 미등록
- API 키 만료

## 카톡은 오는데 그림이 없음

카카오가 raw URL에서 이미지를 못 가져온 것. 원인:
- 저장소가 Private (Public이어야 함)
- raw 캐시 갱신 지연 (sleep 시간 늘리기)
- 이미지 파일이 실제로 안 만들어졌음

## 그림이 잘려서 보임

카카오 카드는 가로가 긴 이미지(2:1 정도)를 선호.

해결: `main.py`의 `figsize=(16, 9)` 가 올바른지 확인.

## 한글이 깨짐 (□□□)

원인: matplotlib에 한글 폰트가 없음.

해결: workflow YAML의 `Install Korean fonts` 단계가 있는지 확인. 그리고 `main.py` 상단의 `for path in fm.findSystemFonts(): if "NanumGothic" in path: ...` 부분 확인.

---

# 유지보수

## refresh_token 갱신 (약 2개월 주기)

`refresh_token`은 약 2개월 (정확히는 60일) 만료. 그 안에 갱신 안 하면 카톡 전송이 멈춤.

갱신 시점: 워크플로우 실행 로그에 `KOE316` 또는 `invalid_token` 비슷한 에러가 뜨기 시작하면 만료된 것.

대응: Phase D를 한 번 더 실행해서 새 refresh_token 발급 → GitHub Secrets의 `KAKAO_REFRESH_TOKEN` 업데이트.

> 💡 더 깔끔하게는, 매번 access_token 갱신할 때 새 refresh_token도 같이 받아서 자동 업데이트하는 코드를 만들 수도 있음 (선택사항).

## 기상청 API 키 만료

KMA 인증키는 **2년** 유효. 만료 임박 시 apihub.kma.go.kr 마이페이지에서 재발급 후 GitHub Secrets의 `KMA_API_KEY` 업데이트.

## GitHub Secrets 보안

키가 노출됐다고 의심되면 (캡처 공유, 코드 실수로 commit 등):
- 카카오 콘솔에서 키 재발급 (플랫폼 키 → ⋮ → 재발급)
- KMA 인증키 재발급
- 새 값으로 GitHub Secrets 업데이트

## 다른 부이로 변경

`main.py` 의 `POHANG_STN = "22106"` 값을 다른 부이의 STN_ID로 변경.

전체 부이 목록은 Phase B-4의 URL에서 `stn=0` 으로 호출하면 볼 수 있음.

## 다른 변수 추가

`main.py`의 `parse_response` 함수에서 추출하는 컬럼을 늘리고, `make_plot`에 서브플롯을 추가하면 됨. 사용 가능한 컬럼:

| 인덱스 | 약자 | 의미 |
|---|---|---|
| 0 | TM | 시간 |
| 2 | WD1 | 풍향 |
| 3 | WS1 | 풍속 |
| 4 | WS1_GST | GUST 풍속 |
| 8 | PA | 해면기압 |
| 9 | HM | 상대습도 |
| 10 | TA | 기온 |
| 11 | TW | 해수면 온도 |
| 12 | WH_MAX | 최대파고 |
| 13 | WH_SIG | 유의파고 |
| 14 | WH_AVE | 평균파고 |
| 15 | WP | 파주기 |
| 16 | WO | 파향 |

---

# 부록: 더 간단한 대안

## 텔레그램으로 변경

카카오 OAuth가 너무 복잡하면 텔레그램이 훨씬 간단합니다 (토큰 만료 없음, 5분 셋업).

1. 텔레그램에서 `@BotFather` 검색 → `/newbot` → 봇 토큰 받기
2. 본인 계정으로 그 봇과 1:1 대화 시작
3. `https://api.telegram.org/bot<토큰>/getUpdates` 에서 본인의 chat_id 확인
4. `send_kakao.py` 대신 다음 코드 사용:

```python
import os, requests
TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]
with open("plots/latest.png", "rb") as f:
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",
        data={"chat_id": TG_CHAT_ID, "caption": "포항 부이 일일보고"},
        files={"photo": f},
    )
```

이미지를 직접 업로드하므로 GitHub raw URL 같은 것 필요 없고 훨씬 안정적.

## 이메일로 변경

가장 간단. SMTP 라이브러리(파이썬 내장 `smtplib`) + Gmail의 앱 비밀번호로 5분이면 끝.

---

# 라이센스 / 데이터 출처

- 기상청 API허브: 기상청 (data.kma.go.kr)
- 카카오 메시지 API: 카카오 (developers.kakao.com)
- 본 코드: 자유롭게 수정·배포 가능 (개인용)

---

*이 매뉴얼은 처음 시도하시는 분들이 자주 막히는 곳을 모두 표시한 실제 구축 경험을 기반으로 합니다.*
