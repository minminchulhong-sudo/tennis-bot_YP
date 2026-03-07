import telebot
import time
import os

# GitHub Secrets에서 환경변수를 가져옵니다.
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

bot = telebot.TeleBot(TOKEN)

def send_messages():
    start_time = time.time()
    # GitHub Action 최대 실행 시간(6시간)을 고려하여 5.5시간 동안만 실행
    timeout = 5.5 * 3600 
    
    print("텔레그램 메시지 전송 시작 (10초 간격)")
    
    while time.time() - start_time < timeout:
        try:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            message = f"[{current_time}] 10초 간격 자동 알림입니다."
            bot.send_message(CHAT_ID, message)
            print(f"전송 완료: {current_time}")
        except Exception as e:
            print(f"오류 발생: {e}")
        
        time.sleep(10) # 10초 대기

if __name__ == "__main__":
    if TOKEN and CHAT_ID:
        send_messages()
    else:
        print("에러: TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID가 설정되지 않았습니다.")
