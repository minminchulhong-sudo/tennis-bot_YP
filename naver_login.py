# -*- coding: utf-8 -*-
# 크롬 셀레니움으로 네이버 로그인하는 프로그램
# 사용법: python naver_login.py
# 아이디/비밀번호는 아래 NAVER_ID / NAVER_PW 값을 수정하거나
# 환경변수 NAVER_ID, NAVER_PW 로 설정하면 됩니다.

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import time

# ====== 사용자 설정 ======
NAVER_ID = os.environ.get("NAVER_ID", "111")   # 아이디 (가정: 111)
NAVER_PW = os.environ.get("NAVER_PW", "222")   # 비밀번호 (가정: 222)
LOGIN_URL = "https://nid.naver.com/nidlogin.login"
HEADLESS = False  # 화면 없이 실행하려면 True
# ==========================


def create_driver():
    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 자동화 탐지 완화 (없으면 네이버가 봇으로 감지해서 캡차를 띄울 확률이 높음)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def naver_login(driver, user_id, user_pw):
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, 10)

    # 아이디/비밀번호 입력창이 뜰 때까지 대기
    id_input = wait.until(EC.presence_of_element_located((By.ID, "id")))
    pw_input = driver.find_element(By.ID, "pw")

    # ⚠️ send_keys()로 직접 타이핑하면 네이버가 자동입력 방지 문자를 띄우므로
    #    JavaScript로 값을 넣는 방식을 사용
    driver.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
        id_input, user_id,
    )
    time.sleep(0.5)
    driver.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
        pw_input, user_pw,
    )
    time.sleep(0.5)

    # 로그인 버튼 클릭
    driver.find_element(By.ID, "log.login").click()
    time.sleep(3)

    # 로그인 성공 여부 확인
    current_url = driver.current_url
    if "nidlogin" not in current_url:
        print(f"✅ 로그인 성공! 현재 페이지: {current_url}")
        return True

    # 실패 시 에러 메시지 출력 (아이디/비번 오류, 캡차 등)
    try:
        error = driver.find_element(By.CSS_SELECTOR, ".error_message, #err_common").text.strip()
        print(f"❌ 로그인 실패: {error}")
    except Exception:
        print("❌ 로그인 실패: 캡차 또는 추가 인증이 필요할 수 있습니다.")
    return False


if __name__ == "__main__":
    driver = create_driver()
    try:
        naver_login(driver, NAVER_ID, NAVER_PW)
        time.sleep(5)  # 결과 확인용 대기
    finally:
        driver.quit()
