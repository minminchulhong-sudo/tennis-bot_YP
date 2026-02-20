from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
from datetime import datetime, date
import os
from bs4 import BeautifulSoup

# ====== 설정 ======
os.environ['TZ'] = 'Asia/Seoul'

TELEGRAM_TOKEN = '7823240483:AAGsHJTezcJRrC3zrILVp5qARkESGkKyah0'
CHAT_ID_MC = '1595617824'
CHAT_ID = "-1002561401824"

URL_LIST = [
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-02", "start_date": date(2026, 1, 25)},
    {"url": "https://srent.y-sisul.or.kr/page/rent/s04.od.list.asp?sch_sym=2026-03", "start_date": date(2026, 2, 25)},
]

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, data={'chat_id': chat_id, 'text': text})
    except: pass

def run_check():
    print("🚀 테니스 코트 확인 시작...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 아래 부분을 더 최신 브라우저 정보로 교체
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("lang=ko_KR") # 한국어 설정 추가
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # [핵심] 쿠키나 리퍼러 정보를 수동으로 주입 (서버를 속이는 기술)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    })
    messages_to_send = []

    try:
        for item in URL_LIST:
            url = item["url"]
            print(f"🔎 접속 중: {url}")
            driver.get(url)
            
            # 1. 달력 데이터(td)가 나타날 때까지 최대 15초 대기
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "td"))
                )
            except:
                print(f"⚠️ {url}: 15초 내에 데이터를 찾지 못했습니다.")
                # 만약 실패하면 페이지에 어떤 글자가 있는지 로그를 남김 (진단용)
                body_text = driver.find_element(By.TAG_NAME, "body").text[:100]
                print(f"현재 페이지 본문 일부: {body_text}")
                continue

            calendar_cells = driver.find_elements(By.CSS_SELECTOR, "td")
            print(f"✅ 발견된 셀 개수: {len(calendar_cells)}")

            for cell in calendar_cells:
                html = cell.get_attribute("innerHTML")
                if "예약가능" in html or "status_y" in html:
                    # ... (이하 날짜 파싱 및 메시지 생성 로직 동일) ...
                    soup = BeautifulSoup(html, "html.parser")
                    h6 = soup.find("h6")
                    if h6:
                        day = int(h6.text.strip())
                        y_m = url.split('sch_sym=')[1][:7]
                        y, m = map(int, y_m.split('-'))
                        check_date = date(y, m, day)
                        
                        # 간단히 주말 조건만 예시로 넣음
                        if check_date >= item["start_date"] and check_date.weekday() in [5, 6]:
                            msg = f"🎾 양평누리 예약 가능: {check_date} (주말)\n🔗 {url}"
                            messages_to_send.append(msg)

        if messages_to_send:
            for msg in messages_to_send: send_telegram(CHAT_ID, msg)
        else:
            print("잔여 코트 없음")

    except Exception as e:
        send_telegram(CHAT_ID_MC, f"오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run_check()

