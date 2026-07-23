import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

import cv2
import base64
import paho.mqtt.client as mqtt
import time
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import sys

# --- RTSP 與 Topic 對應 ---
stream_configs = {
    "USC/front": "rtsp://admin:admini@colin.hr-env.com:10554/stream2",
    "USC/side":  "rtsp://admin:admini@colin.hr-env.com:20554/stream2",
    "USC/top":   "rtsp://admin:admini@colin.hr-env.com:40554/stream2", } # 192.0.2.123 是保留 IP，不會有服務

# --- MQTT 設定 ---
MQTT_BROKER = "voiplab.niu.edu.tw"
MQTT_PORT = 1883

mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

# 結束旗標
stop_event = threading.Event()

# 你的 Email 設定
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_ADDRESS = "sony20666262@gmail.com"
EMAIL_PASSWORD = "cbcikknwzcvqllza"  # 建議使用 Gmail App Password
EMAIL_RECEIVER = "voiplab.niu@gmail.com"


def send_email(subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.set_debuglevel(1)  # SMTP 通訊詳細印出，幫你看問題
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("[Email] 發送成功")
    except Exception as e:
        print(f"[Email] 發送失敗: {e}")


connected_streams = set()
failed_streams = set()

connected_streams_lock = threading.Lock()
failed_streams_lock = threading.Lock()

email_sent = False
fail_email_sent = False
last_fail_set = set()  # 記錄最後一次失敗串流清單

def send_success_email():
    global email_sent
    if not email_sent:
        send_email(
            "所有串流已成功連接",
            f"串流 {', '.join(sorted(connected_streams))} 全部連接成功。"
        )
        email_sent = True

def send_failure_email():
    print("[Debug] send_failure_email() 被呼叫")
    global fail_email_sent, last_fail_set
    with failed_streams_lock:
        if failed_streams != last_fail_set:
            fail_email_sent = False
            last_fail_set = failed_streams.copy()
        else:
            return
    if failed_streams:
        body = f"以下串流連接失敗：{', '.join(sorted(failed_streams))}"
        print(f"[Debug] 寄信內容: {body}")
        print(f"[Debug] 收件人: {EMAIL_RECEIVER}")
        send_email("串流連接失敗通知", body)
        fail_email_sent = True





def check_status_and_notify():
    global email_sent, fail_email_sent
    with connected_streams_lock, failed_streams_lock:
        total = len(stream_configs)
        success_count = len(connected_streams)
        fail_count = len(failed_streams)

        # 全部成功
        if success_count == total:
            # 重置失敗信狀態（未失敗）
            fail_email_sent = False
            send_success_email()

        # 有失敗（不管有沒有全部成功）
        elif fail_count > 0:
            # 成功信標記為未寄（因為沒全成功）
            email_sent = False
            send_failure_email()

def stream_worker(topic, rtsp_url):
    retry_count = 0

    while not stop_event.is_set():
        print(f"[{topic}] 迴圈開始，retry_count={retry_count}")
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if cap.isOpened():
            print(f"[{topic}] 成功連接 RTSP")
            with connected_streams_lock:
                connected_streams.add(topic)
            with failed_streams_lock:
                failed_streams.discard(topic)
            check_status_and_notify()
            retry_count = 0

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"[{topic}] 原始解析度：{width}x{height}")

            frame_count = 0
            last_time = time.time()

            while cap.isOpened() and not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    print(f"[{topic}] 影像讀取錯誤或結束，嘗試重新連接...")
                    break

                frame_count += 1
                current_time = time.time()
                elapsed = current_time - last_time
                if elapsed >= 1.0:
                    fps = frame_count / elapsed
                    print(f"[{topic}] FPS：{fps:.2f}")
                    frame_count = 0
                    last_time = current_time

                _, buffer = cv2.imencode('.jpg', frame)
                b64 = base64.b64encode(buffer).decode()
                mqtt_client.publish(topic, b64)

            cap.release()
        else:
            retry_count += 1
            print(f"[{topic}] 無法連接 RTSP，重試中...({retry_count})")
            with failed_streams_lock:
                failed_streams.add(topic)
            with connected_streams_lock:
                connected_streams.discard(topic)
            check_status_and_notify()
            try:
                cap.release()
            except Exception:
                pass

            wait_sec = min(2 * retry_count, 30)
            print(f"[{topic}] 等待 {wait_sec} 秒後重試")
            time.sleep(wait_sec)

    print(f"[{topic}] 結束串流")




# 啟動所有串流 thread
threads = []
for topic, rtsp_url in stream_configs.items():
    t = threading.Thread(target=stream_worker, args=(topic, rtsp_url))
    t.start()
    threads.append(t)

# 主執行緒等待 q 鍵結束
try:
    print("按下 q 然後 Enter 可結束所有串流")
    while True:
        user_input = input()
        if user_input.strip().lower() == 'q':
            print("收到結束指令，準備停止所有串流...")
            stop_event.set()
            break
except KeyboardInterrupt:
    print("手動中斷，結束串流")
    stop_event.set()

for t in threads:
    t.join()

mqtt_client.disconnect()
print("已斷線並退出")

