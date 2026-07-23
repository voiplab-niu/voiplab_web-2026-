import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

import cv2
import base64
import paho.mqtt.client as mqtt
import time
import threading

# --- RTSP 與 Topic 對應 ---
stream_configs = {
    "USC/front": "rtsp://111.70.35.91:54200/v1",
    "USC/side":  "rtsp://111.70.35.91:54201/v1",
    "USC/top":   "rtsp://111.70.35.91:54202/v1",
}

# --- MQTT 設定 ---
MQTT_BROKER = "voiplab.niu.edu.tw"
MQTT_PORT = 1883

mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

# 結束旗標
stop_event = threading.Event()

def stream_worker(topic, rtsp_url):
    while not stop_event.is_set():
        max_retries = 500
        retry_count = 0
        cap = None

        while retry_count < max_retries and not stop_event.is_set():
            cap = cv2.VideoCapture(rtsp_url)
            if cap.isOpened():
                print(f"[{topic}] 成功連接 RTSP")
                break
            else:
                print(f"[{topic}] 無法連接 RTSP，重試中...({retry_count + 1})")
                retry_count += 1
                time.sleep(2)

        if retry_count == max_retries or stop_event.is_set():
            print(f"[{topic}] 放棄連線")
            return

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[{topic}] 原始解析度：{width}x{height}")

        frame_count = 0
        last_time = time.time()

        while cap.isOpened() and not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print(f"[{topic}] 影像讀取錯誤或結束，嘗試重新連接...")
                cap.release()
                time.sleep(1)  # 等待1秒後重試
                break  # 跳出內部循環，外部循環會重新建立連接

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
            print(b64)
            mqtt_client.publish(topic, b64)

        cap.release()
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
