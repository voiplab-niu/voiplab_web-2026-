import paho.mqtt.client as mqtt
import time
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from tqdm import tqdm


# MQTT 設定
MQTT_BROKER = "voiplab.niu.edu.tw"
MQTT_PORT = 1883
TOPICS = ["USC/front", "USC/side", "USC/top"]

# Email 設定
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_ADDRESS = "sony20666262@gmail.com"
EMAIL_PASSWORD = "mxrdzurhbaqgqrqd"
EMAIL_RECEIVER = "voiplab.niu@gmail.com"

# 上次收到訊息時間字典 (初始化為當前時間，避免一開始就寄信)
last_received = {topic: time.time() for topic in TOPICS}

# 進度條最大時間 (秒)
MAX_WAIT = 30

# 是否已寄信（避免重複寄）
email_sent = {topic: False for topic in TOPICS}

def send_email(subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print(f"[Email] 寄信成功: {subject}")
    except Exception as e:
        print(f"[Email] 寄信失敗: {e}")

def on_message(client, userdata, msg):
    topic = msg.topic
    last_received[topic] = time.time()
    # 收到訊息後重設寄信狀態
    email_sent[topic] = False

def monitor():
    # tqdm 進度條列表
    bars = {topic: tqdm(total=MAX_WAIT, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}s', position=i) for i, topic in enumerate(TOPICS)}

    while True:
        now = time.time()
        for topic, bar in bars.items():
            elapsed = now - last_received[topic]
            if elapsed > MAX_WAIT:
                bar.n = MAX_WAIT
                if not email_sent[topic]:
                    send_email(
                        f"[警告] {topic} 超過 {MAX_WAIT} 秒未收到訊息",
                        f"{topic} 已超過 {MAX_WAIT} 秒沒有收到 MQTT 訊息，請檢查串流或設備狀態。"
                    )
                    email_sent[topic] = True
            else:
                bar.n = elapsed
            bar.refresh()
        time.sleep(0.1)

def main():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    for topic in TOPICS:
        client.subscribe(topic)
    client.loop_start()

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("結束程式")
        client.loop_stop()

if __name__ == "__main__":
    main()

