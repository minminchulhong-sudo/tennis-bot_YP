from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests
import time
from datetime import datetime, date
import os
from bs4 import BeautifulSoup

# ====== 공휴일 목록 ======
HOLIDAYS = [
    date(2026, 3, 2),   # 어린이날
    date(2026, 5, 5),   # 대체공휴일
    date(2026, 5, 25),   # 대선
    date(2026, 6, 3),   # 대선
    date(2026, 7, 17),   # 현충일
    date(2026, 6, 6),   # 현충일
    date(2026, 8, 17),  # 광복절
    date(2026, 10, 5),  # 개천절
    date(2026, 9, 24),  # 추석 연휴
    date(2026, 9, 25),  # 추석
    date(2026, 10, 9),  # 
    date(2026, 12, 25)  # 크리스마스
]
WEEKDAYS_KR = ['월', '화', '수', '목', '금', '토', '일']
# ==========================

# ====== 사용자 설정 ======
TELEGRAM_TOKEN = '7823240483:AAGsHJTezcJRrC3zrILVp5qARkESGkKyah0'
CHAT_ID_MC = '1595617824'
CHAT_ID = "-1002561401824"

CHECK_INTERVAL = 900  # 5분
LOG_FILE = "log_YP.txt"
URL_LIST = [
#    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2025-04", "start_date": date(2026, 3, 25)},
#    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2025-05", "start_date": date(2026, 4, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2025-06", "start_date": date(2026, 5, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2025-07", "start_date": date(2026, 6, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2025-08", "start_date": date(2026, 7, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2025-09", "start_date": date(2026, 8, 25)},
]
# ==========================

def auto_delete_log_if_old():
    if os.path.exists(LOG_FILE):
        last_modified = os.path.getmtime(LOG_FILE)
        age_in_days = (time.time() - last_modified) / (60 * 60 * 24)
        if age_in_days >= 7:
            os.remove(LOG_FILE)
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 오래된 로그 삭제됨. 새로 시작.\n")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': text}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"텔레그램 전송 오류: {e}")

def send_telegram_to_MC(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID_MC, 'text': text}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"텔레그램 전송 오류: {e}")

def write_log(msg):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {msg}\n")

# 로그 자동 삭제
auto_delete_log_if_old()

# 시작 알림
send_telegram_to_MC("✅ 양평누리 테니스 잔여 코트 확인 봇이 실행되었습니다.\n【ver.05140831】")
write_log("✅ 예약 확인 봇 시작됨.")

while True:
    try:
        now = datetime.now()
        current_hour = now.hour
        current_day = now.day

        if current_day <= 24:
            # 1~24일: 0~9시는 검사 생략
            if 0 <= current_hour < 10:
                write_log("🌙야간 시간 검사 생략 (0시~10시)")
                time.sleep(3600)
                continue
        else:
            # 25일 이후: 0~10시, 19~23시는 검사 생략
            if not (11 <= current_hour < 18):
                write_log("🌙야간 시간 검사 생략 (0시~11시 및 18시~24시)")
                time.sleep(3600)
                continue
        
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        messages_to_send = [] 

        for item in URL_LIST:
            url = item["url"]
            start_date = item["start_date"]
        
            # ✅ 오늘이 감시 시작일보다 이전이면 이 URL은 아직 감시하지 않음
            if date.today() < start_date:
                write_log(f"⏳ 감시 시작 전이므로 건너뜀 → (감시 시작일: {start_date})")
                continue  # 🚫 driver.get()도 실행하지 않음
        
            driver.get(url)
            time.sleep(2)

            calendar_cells = driver.find_elements(By.CSS_SELECTOR, "td")

            for cell in calendar_cells:
                html = cell.get_attribute("innerHTML")
                soup = BeautifulSoup(html, "html.parser")

                h6 = soup.find("h6")
                if not h6:
                    continue

                try:
                    day = int(h6.text.strip())
                    y, m = int(url[-7:-2].split('-')[0]), int(url[-2:])
                    check_date = date(y, m, day)
                except:
                    continue

                # ✅ 감시 시작일 이전은 무시
                if check_date < start_date:
                    continue

                # ✅ 주말 또는 공휴일 감시
                if check_date.weekday() in [5, 6] or check_date in HOLIDAYS:
                    if "예약가능" in html or "status_y" in html:
                        label = "공휴일" if check_date in HOLIDAYS else "주말"
                        weekday_kr = WEEKDAYS_KR[check_date.weekday()]
                        message = f"🎾 예약 알림: 양평누리 {check_date.strftime('%Y-%m-%d')} ({weekday_kr}, {label}) 예약 가능!\n🔗 {url}"
                        messages_to_send.append(message)
                        write_log(f"예약 가능 슬롯 발견됨 → {check_date} → {url}")
                        write_log(f"검사 날짜: {check_date}, 시작 기준일: {start_date}, URL={url}")

        if messages_to_send:
            for msg in messages_to_send:
                send_telegram_message(msg)
        else:
            msg = f"[{time.strftime('%H:%M:%S')}] 아직 없음! - 다음 확인까지 대기"
            print(msg)
            write_log(msg)

        driver.quit()
        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        error_msg = f"❌ 양평누리 봇 오류 발생: {e}"
        print(error_msg)
        write_log(error_msg)
        send_telegram_to_MC(error_msg) 
        time.sleep(CHECK_INTERVAL)

