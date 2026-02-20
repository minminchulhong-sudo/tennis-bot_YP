from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import requests
import time
from datetime import datetime, date
import os
from bs4 import BeautifulSoup

# ====== 설정 (기존과 동일) ======
os.environ['TZ'] = 'Asia/Seoul' # 한국 시간 설정

HOLIDAYS = [
    date(2026, 3, 2), date(2026, 5, 5), date(2026, 5, 25), date(2026, 6, 3),
    date(2026, 7, 17), date(2026, 6, 6), date(2026, 8, 17), date(2026, 10, 5),
    date(2026, 9, 24), date(2026, 9, 25), date(2026, 10, 9), date(2026, 12, 25)
]
WEEKDAYS_KR = ['월', '화', '수', '목', '금', '토', '일']

TELEGRAM_TOKEN = '7823240483:AAGsHJTezcJRrC3zrILVp5qARkESGkKyah0'
CHAT_ID_MC = '1595617824'
CHAT_ID = "-1002561401824"

URL_LIST = [
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-02", "start_date": date(2026, 1, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-03", "start_date": date(2026, 2, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-04", "start_date": date(2026, 3, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-05", "start_date": date(2026, 4, 25)},
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

def run_check():
    print("🚀 양평누리 테니스 코트 확인을 시작합니다...")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    messages_to_send = []

    try:
        for item in URL_LIST:
            url = item["url"]
            start_date = item["start_date"]

            if date.today() < start_date:
                continue

            driver.get(url)
            time.sleep(5) # 페이지 로딩 대기

            calendar_cells = driver.find_elements(By.CSS_SELECTOR, "td")
            
            if len(calendar_cells) == 0:
                print(f"⚠️ {url} 에서 데이터를 찾지 못했습니다.")
                continue # 다음 URL로 이동

            # [수정 포인트 1] 루프를 if 블록 밖으로 꺼냈습니다.
            for cell in calendar_cells:
                html = cell.get_attribute("innerHTML")
                
                # 예약 가능 여부 먼저 체크 (성능 향상)
                if "예약가능" in html or "status_y" in html:
                    soup = BeautifulSoup(html, "html.parser")
                    h6 = soup.find("h6")
                    if not h6: continue

                    try:
                        day = int(h6.text.strip())
                        y_m_part = url.split('sch_sym=')[1][:7]
                        y, m = map(int, y_m_part.split('-'))
                        check_date = date(y, m, day)
                    except: continue

                    # 주말/공휴일 체크
                    if check_date >= start_date:
                        if check_date.weekday() in [5, 6] or check_date in HOLIDAYS:
                            label = "공휴일" if check_date in HOLIDAYS else "주말"
                            weekday_kr = WEEKDAYS_KR[check_date.weekday()]
                            message = f"🎾 양평누리 예약 가능!\n{check_date.strftime('%Y-%m-%d')} ({weekday_kr}, {label})\n🔗 {url}"
                            messages_to_send.append(message)

        # [수정 포인트 2] 모든 URL 확인 후 결과 전송 (루프 밖으로 이동)
        if messages_to_send:
            for msg in messages_to_send:
                send_telegram_message(msg)
        else:
            print("현재 예약 가능한 슬롯이 없습니다.")
            send_telegram_to_MC("확인 완료: 예약 가능 슬롯 없음")

    except Exception as e:
        error_msg = f"❌ 실행 중 오류 발생: {e}"
        print(error_msg)
        send_telegram_to_MC(error_msg)
    finally:
        driver.quit()
        print("✅ 검사가 완료되었습니다.")

if __name__ == "__main__":
    run_check()
