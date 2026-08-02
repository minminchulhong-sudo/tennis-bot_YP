from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import re
from datetime import date
from html import escape
import os
from bs4 import BeautifulSoup

# ====== 설정 ======
os.environ['TZ'] = 'Asia/Seoul'

TELEGRAM_TOKEN = '7823240483:AAGsHJTezcJRrC3zrILVp5qARkESGkKyah0'
CHAT_ID_MC = '1595617824'
CHAT_ID = "-1002561401824"

BASE_URL = "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym={ym}"

# ====== 공휴일 목록 ======
HOLIDAYS = [
    date(2026, 3, 2),
    date(2026, 5, 5),
    date(2026, 5, 25),
    date(2026, 6, 3),
    date(2026, 6, 6),
    date(2026, 7, 17),
    date(2026, 8, 17),
    date(2026, 9, 24),
    date(2026, 9, 25),
    date(2026, 10, 5),
    date(2026, 10, 9),
    date(2026, 12, 25),
]
WEEKDAYS_KR = ['월', '화', '수', '목', '금', '토', '일']

# 예약 오픈 규칙: 다음 달 페이지는 이번 달 25일부터 감시
NEXT_MONTH_OPEN_DAY = 25


def build_url_list(today):
    """이번 달 + (25일 이후라면) 다음 달 감시 URL 목록 생성"""
    url_list = [{"ym": f"{today.year}-{today.month:02d}", "min_date": today}]
    if today.day >= NEXT_MONTH_OPEN_DAY:
        ny, nm = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        url_list.append({"ym": f"{ny}-{nm:02d}", "min_date": today})
    for item in url_list:
        item["url"] = BASE_URL.format(ym=item["ym"])
    return url_list


def send_telegram(chat_id, text, html=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # 텔레그램 메시지 최대 길이(4096자) 대비, HTML 태그가 깨지지 않게 줄 단위로 분할 전송
    chunks, current = [], ""
    for line in text.split("\n"):
        if current and len(current) + len(line) + 1 > 4000:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)

    for chunk in chunks:
        payload = {'chat_id': chat_id, 'text': chunk}
        if html:
            payload['parse_mode'] = 'HTML'
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print(f"텔레그램 전송 오류: {e}")


# 시간대 표기: "10:00~12:00", "10시~12시", "10 ~ 12" 등 다양한 형태 대응
TIME_RE = re.compile(r'(\d{1,2})\s*(?:[:시]\s*(\d{1,2}))?\s*분?\s*[~∼〜～-]\s*(\d{1,2})\s*(?:[:시]\s*(\d{1,2}))?\s*분?')


def format_hour(hour, minute):
    h = int(hour)
    m = int(minute) if minute else 0
    return f"{h}시" if m == 0 else f"{h}시{m:02d}분"


def extract_slots(cell_html):
    """달력 셀 HTML에서 예약가능 항목별 (시간대, 코트명) 목록 추출.
    구조를 못 읽으면 빈 문자열로 반환해 날짜 단위 알림으로 대체."""
    soup = BeautifulSoup(cell_html, "html.parser")

    def is_available(tag):
        cls = " ".join(tag.get("class") or [])
        return "status_y" in cls or "예약가능" in tag.get_text()

    tag_names = ["li", "a", "p", "dd", "div", "span"]
    matched = [t for t in soup.find_all(tag_names) if is_available(t)]
    # 하위에 또 다른 매칭 태그가 있는 상위 태그는 제외하고 최소 단위만 사용
    leaves = [t for t in matched
              if not any(d is not t and is_available(d) for d in t.find_all(tag_names))]

    slots = []
    for tag in leaves:
        text = tag.get_text(" ", strip=True)
        m = TIME_RE.search(text)
        if m:
            time_label = f"{format_hour(m.group(1), m.group(2))}~{format_hour(m.group(3), m.group(4))}"
        else:
            time_label = ""
        # 코트명 = 시간/상태 문구를 제거한 나머지 텍스트
        court = TIME_RE.sub(" ", text)
        court = re.sub(r'예약\s*가능|예약가능|\[|\]|\(\s*\)', " ", court)
        court = re.sub(r'\s+', " ", court).strip(" -·,")
        slots.append((time_label, court))

    if not slots:
        slots.append(("", ""))
    return slots


def time_sort_key(time_label):
    m = re.match(r'(\d{1,2})', time_label)
    return (0, int(m.group(1))) if m else (1, 0)


def build_message(results, links):
    """수집 결과를 날짜-시간 순으로 정리한 하나의 메시지 생성 (텔레그램 HTML 포맷)"""
    lines = ["🎾 <b>양평누리 테니스 예약 가능 현황</b>", ""]

    for d in sorted(results):
        label = "주말" if d.weekday() in [5, 6] else "공휴일"
        lines.append(f"📅 <b>{d.month}월 {d.day}일 ({WEEKDAYS_KR[d.weekday()]}, {label})</b>")

        slot_map = results[d]
        for time_label in sorted(slot_map, key=time_sort_key):
            courts = [escape(c) for c in dict.fromkeys(slot_map[time_label]) if c]
            court_text = ", ".join(courts) if courts else "예약가능 (상세는 링크 확인)"
            lines.append(f"⏰ {time_label}: {court_text}" if time_label else f"⏰ {court_text}")
        lines.append("")

    lines.append("🔗 <b>예약 링크</b>")
    for label, url in links:
        lines.append(f'{escape(label)}: {escape(url)}')

    return "\n".join(lines)


def run_check():
    print("🚀 테니스 코트 확인 시작...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("lang=ko_KR")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    })

    today = date.today()
    results = {}   # date -> {시간대: [코트명, ...]}
    links = []     # (라벨, URL) - 예약가능 항목이 나온 페이지만

    try:
        for item in build_url_list(today):
            url = item["url"]
            print(f"🔎 접속 중: {url}")
            driver.get(url)

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "td"))
                )
            except:
                print(f"⚠️ {url}: 15초 내에 데이터를 찾지 못했습니다.")
                body_text = driver.find_element(By.TAG_NAME, "body").text[:100]
                print(f"현재 페이지 본문 일부: {body_text}")
                continue

            calendar_cells = driver.find_elements(By.CSS_SELECTOR, "td")
            print(f"✅ 발견된 셀 개수: {len(calendar_cells)}")

            month_has_slot = False
            y, m = map(int, item["ym"].split('-'))

            for cell in calendar_cells:
                html = cell.get_attribute("innerHTML")
                if "예약가능" not in html and "status_y" not in html:
                    continue

                soup = BeautifulSoup(html, "html.parser")
                h6 = soup.find("h6")
                if not h6:
                    continue
                try:
                    day = int(h6.text.strip())
                    check_date = date(y, m, day)
                except:
                    continue

                if check_date < item["min_date"]:
                    continue
                if check_date.weekday() not in [5, 6] and check_date not in HOLIDAYS:
                    continue

                month_has_slot = True
                slot_map = results.setdefault(check_date, {})
                for time_label, court in extract_slots(html):
                    slot_map.setdefault(time_label, []).append(court)
                print(f"예약 가능 발견 → {check_date}")

            if month_has_slot:
                links.append((f"{m}월", url))

        if results:
            message = build_message(results, links)
            print(message)
            send_telegram(CHAT_ID, message, html=True)
        else:
            print("잔여 코트 없음")

    except Exception as e:
        send_telegram(CHAT_ID_MC, f"오류 발생: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    run_check()
