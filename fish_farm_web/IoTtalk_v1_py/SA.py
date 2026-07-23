import time
import requests
import json
from datetime import datetime
import sqlite3
import csv
import random

# 伺服器和MQTT相關設定
ServerURL ='https://iottalk.niu.edu.tw'
MQTT_broker = 'iottalk.niu.edu.tw'
MQTT_port = 1884
MQTT_encryption = True
MQTT_User = 'iottalk'
MQTT_PW = 'iottalk2023'

# 設備模型和ID
device_model = 'Fish-Farm-sensor'
IDF_list = ['DO-I','ORP-I','PH-I','Salinity-I','Temperature-I']
ODF_list = []

device_id = str(random.randint(10000, 99999))
device_name = 'Composite_Sensor0826'
APIServerURL_1 = 'http://colin.hr-env.com/System/Record/GetLastRecord?eid=30091'
APIServerURL_2 = 'http://colin.hr-env.com/System/Record/GetLastRecord?eid=30092'
APIServerURL_3 = 'http://colin.hr-env.com/System/Record/GetLastRecord?eid=30093'
exec_interval = 1

lat = 24.745313
lng = 121.745288
current_do_index = 0
current_orp_index = 0
current_ph_index = 0
current_salinity_index = 0
current_temperature_index = 0


def get_current_time():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def fetch_sensor_data(sensor_suffix):
    json_results = []
    # 定義 API 與對應的 Sensor 後綴
    api_servers = [
        (APIServerURL_1, '_Sensor1'),
        (APIServerURL_2, '_Sensor2'),
        (APIServerURL_3, '_Sensor3')
    ]

    for api_url, sensor_tag in api_servers:
        try:
            response = requests.get(api_url)
        except Exception as e:
            print(f"從 {api_url} 取得資料時發生例外: {e}")
            continue

        if response.status_code == 200:
            json_start = response.text.find('{')
            json_end = response.text.rfind('}') + 1
            cleaned_text = response.text[json_start:json_end]

            try:
                data = json.loads(cleaned_text)
            except Exception as e:
                print(f"解析 {api_url} 回傳的 JSON 時發生錯誤: {e}")
                continue

            sensor_data = data.get("SensorData", [])
            if not sensor_data:
                print(f"{api_url} 回傳的資料中沒有 SensorData")
                continue

            for sensor in sensor_data:
                if sensor.get('T') == sensor_suffix:
                    sensor_type = sensor['T'] + sensor_tag
                    sensor_value = sensor['V']
                    current_time = get_current_time()
                    send_time = time.time()
                    data_to_save = [lat, lng, sensor_type, sensor_value, current_time, send_time]

                    save_to_database(data_to_save)
                    save_to_csv(data_to_save)
                    
                    json_data = {
                        "lat": lat,
                        "lng": lng,
                        "sensor": sensor_type,
                        "value": sensor_value,
                        "timestamp": current_time,
                        "send_time":round(time.time(), 5)  # 秒數 + 小數點

                    }
                    
                    json_results.append(json.dumps(json_data))
                    break  
        else:
            print(f"從 {api_url} 取得資料失敗。Status code: {response.status_code}")

    # 回傳一個字串，每筆 JSON 以換行符號分隔
    if json_results:
        return "\n".join(json_results)
    else:
        print(f"找不到符合 {sensor_suffix} 條件的傳感器資料")
        return None




def save_to_csv(data):
    csv_path = r"C:\Users\sony2\Desktop\fish_farm\data.csv"
    try:
        with open(csv_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data)
            # print("Data saved to CSV successfully.")
    except Exception as e:
        print(f"Error saving to CSV: {e}")


def save_to_database(data):
    db_path = r"C:\Users\sony2\Desktop\fish_farm\DATA.db"
    
    conn = None
    try:
        # 只取前五個欄位寫入資料庫
        data_for_db = data[:5]

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO DATA (latitude, longitude, sensor_type, sensor_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', data_for_db)

        conn.commit()
        conn.close()
    
    except sqlite3.IntegrityError as e:
        print(f"Integrity error: {e} - Data: {data}")
    except sqlite3.Error as e:
        print(f"Database error: {e} - Data: {data}")



def is_time_to_save(last_saved_time):
    now = datetime.now()
    if now.minute % 5 == 0 and now.minute != last_saved_time:
        return True
    return False

def DO_I():
    global current_do_index

    data = fetch_sensor_data("DO")  # 多筆 JSON 字串，每行一筆
    if data:
        lines = data.strip().split("\n")  # 分割每行
        total_lines = len(lines)

        if total_lines == 0:
            return None  # 沒有資料

        # 取目前這一筆（加上循環）
        line = lines[current_do_index % total_lines]

        try:
            sensor = json.loads(line)
            current_do_index += 1  # 移動到下一筆（自動循環）
            return sensor['lat'], sensor['lng'], sensor['sensor'], sensor['value'], sensor['timestamp'], sensor['send_time']
        except Exception as e:
            return None  # 或印出錯誤訊息
    else:
        return None  # 沒抓到資料



def ORP_I():
    global current_orp_index

    data = fetch_sensor_data("ORP")  # 多筆 JSON 字串，每行一筆
    if data:
        lines = data.strip().split("\n")  # 分割每行
        total_lines = len(lines)

        if total_lines == 0:
            return None  # 沒有資料

        # 取目前這一筆（加上循環）
        line = lines[current_orp_index % total_lines]

        try:
            sensor = json.loads(line)
            current_orp_index += 1  # 移動到下一筆（自動循環）
            return sensor['lat'], sensor['lng'], sensor['sensor'], sensor['value'], sensor['timestamp'], sensor['send_time']
        except Exception as e:
            return None  # 或印出錯誤訊息
    else:
        return None  # 沒抓到資料
    

def Salinity_I():
    global current_salinity_index

    data = fetch_sensor_data("Salinity")  # 多筆 JSON 字串，每行一筆
    if data:
        lines = data.strip().split("\n")  # 分割每行
        total_lines = len(lines)

        if total_lines == 0:
            return None  # 沒有資料

        # 取目前這一筆（加上循環）
        line = lines[current_salinity_index % total_lines]

        try:
            sensor = json.loads(line)
            current_salinity_index += 1  # 移動到下一筆（自動循環）
            return sensor['lat'], sensor['lng'], sensor['sensor'], sensor['value'], sensor['timestamp'], sensor['send_time']
        except Exception as e:
            return None  # 或印出錯誤訊息
    else:
        return None  # 沒抓到資料

def Temperature_I():
    global current_temperature_index

    data = fetch_sensor_data("Temperature")  # 多筆 JSON 字串，每行一筆
    if data:
        lines = data.strip().split("\n")  # 分割每行
        total_lines = len(lines)

        if total_lines == 0:
            return None  # 沒有資料

        # 取目前這一筆（加上循環）
        line = lines[current_temperature_index % total_lines]

        try:
            sensor = json.loads(line)
            current_temperature_index += 1  # 移動到下一筆（自動循環）
            return sensor['lat'], sensor['lng'], sensor['sensor'], sensor['value'], sensor['timestamp'], sensor['send_time']
        except Exception as e:
            return None  # 或印出錯誤訊息
    else:
        return None  # 沒抓到資料
def PH_I():
    global current_ph_index

    data = fetch_sensor_data("PH")  # 多筆 JSON 字串，每行一筆
    if data:
        lines = data.strip().split("\n")  # 分割每行
        total_lines = len(lines)

        if total_lines == 0:
            return None  # 沒有資料

        # 取目前這一筆（加上循環）
        line = lines[current_ph_index % total_lines]

        try:
            sensor = json.loads(line)
            current_ph_index += 1  # 移動到下一筆（自動循環）
            return sensor['lat'], sensor['lng'], sensor['sensor'], sensor['value'], sensor['timestamp'], sensor['send_time']
        except Exception as e:
            return None  # 或印出錯誤訊息
    else:
        return None  # 沒抓到資料
    
    

def DO_O(data: list):
    print(data)

def ORP_O(data: list):
    print(data)

def PH_O(data: list):
    print(data)

def Salinity_O(data: list):
    print(data)

def Temperature_O(data: list):
    print(data)


# 主程序
def main():
    last_saved_minute = -1  # 記錄最後存儲的分鐘

    while True:
        # 持續抓取並即時處理數據
        for sensor in IDF_list:
            data = fetch_sensor_data(sensor)
            if data:
                print(f"Real-time data: {data}")

        # 每5分鐘檢查是否需要存儲數據
        if is_time_to_save(last_saved_minute):
            last_saved_minute = datetime.now().minute  # 更新最後存儲的分鐘
            for sensor in IDF_list:
                data = fetch_sensor_data(sensor)
                if data:
                    save_to_database(data)
                    save_to_csv(data)

        time.sleep(1)  # 每秒執行一次


if __name__ == "__main__":
    main()
