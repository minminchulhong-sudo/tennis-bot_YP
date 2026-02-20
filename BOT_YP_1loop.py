from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests
import time
from datetime import datetime, date
import os
from bs4 import BeautifulSoup

# ====== 공휴일 목록 및 설정 (기존과 동일) ======
HOLIDAYS = [
    date(2026, 3, 2), date(2026, 5, 5), date(2026, 5, 25), date(2026, 6, 3),
    date(2026, 7, 17), date(2026, 6, 6), date(2026, 8, 17), date(2026, 10, 5),
    date(2026, 9, 24), date(2026, 9, 25), date(2026, 10, 9), date(2026, 12, 25)
]
WEEKDAYS_KR = ['월', '화', '수', '목', '금', '토', '일']

TELEGRAM_TOKEN = '7823240483:AAGsHJTezcJRrC3zrILVp5qARkESGkKyah0'
CHAT_ID_MC = '1595617824'
CHAT_ID = "-1002561401824"
LOG_FILE = "log_YP.txt"

URL_LIST = [
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-02", "start_date": date(2026, 1, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-03", "start_date": date(2026, 2, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-04", "start_date": date(2026, 3, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-05", "start_date": date(2026, 4, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-06", "start_date": date(2026, 5, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-07", "start_date": date(2026, 6, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-08", "start_date": date(2026, 7, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-09", "start_date": date(2026, 8, 25)},
]

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': text}
    try: requests.post(url, data=payload)
    except Exception as e: print(f"오류: {e}")

def send_telegram_to_MC(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID_MC, 'text': text}
    try: requests.post(url, data=payload)
    except Exception as e: print(f"오류: {e}")

def write_log(msg):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {msg}\n")

# ====== 실행 로직 (단회 실행용) ======
def run_check():
    print("🚀 양평누리 테니스 코트 확인을 시작합니다...")
    send_telegram_to_MC("🚀 양평누리 테니스 코트 확인을 시작합니다...")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    # 리소스 절약을 위해 창 크기 제한 및 불필요한 로그 끄기
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    messages_to_send = []

    try:
        for item in URL_LIST:
            url = item["url"]
            start_date = item["start_date"]

            # 감시 시작일 이전이면 스킵
            if date.today() < start_date:
                continue

            driver.get(url)
            time.sleep(2) # 페이지 로딩 대기

            calendar_cells = driver.find_elements(By.CSS_SELECTOR, "td")
            for cell in calendar_cells:
                html = cell.get_attribute("innerHTML")
                soup = BeautifulSoup(html, "html.parser")
                h6 = soup.find("h6")
                
                if not h6: continue

                try:
                    day = int(h6.text.strip())
                    # URL 구조에서 연도/월 추출 (예: 2026-02)
                    y_m_part = url.split('sch_sym=')[1]
                    y, m = map(int, y_m_part.split('-'))
                    check_date = date(y, m, day)
                except: continue

                # 주말/공휴일 및 예약 가능 여부 체크
                if check_date >= start_date:
                    if check_date.weekday() in [5, 6] or check_date in HOLIDAYS:
                        if "예약가능" in html or "status_y" in html:
                            label = "공휴일" if check_date in HOLIDAYS else "주말"
                            weekday_kr = WEEKDAYS_KR[check_date.weekday()]
                            message = f"🎾 양평누리 예약 가능!\n{check_date.strftime('%Y-%m-%d')} ({weekday_kr}, {label})\n🔗 {url}"
                            messages_to_send.append(message)

        # 결과 전송
        if messages_to_send:
            for msg in messages_to_send:
                send_telegram_message(msg)
            write_log(f"성공: {len(messages_to_send)}건 발견")
        else:
            print("현재 예약 가능한 슬롯이 없습니다.")
            write_log("확인 완료: 예약 가능 슬롯 없음")

    except Exception as e:
        error_msg = f"❌ 실행 중 오류 발생: {e}"
        print(error_msg)
        send_telegram_to_MC(error_msg)
    finally:
        driver.quit()
        print("✅ 검사가 완료되어 프로그램을 종료합니다.")

if __name__ == "__main__":
    run_check()