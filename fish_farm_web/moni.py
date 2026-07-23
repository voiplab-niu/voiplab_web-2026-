import random
import time
import sqlite3
from datetime import datetime

# 定义一个函数来插入数据到数据库
import sqlite3
from datetime import datetime

def insert_data(temp, water_level, ph, do, rpo, am):
    try:
        conn = sqlite3.connect('C:/Users/user/Desktop/111/as.db') 
        c = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 更新 SQL 插入語句，新增氨氣和氧化還原電位數據
        c.execute('''
            INSERT INTO DATA (TEMP, WATER_LEVEL, PH, DO, RPO, AM,timestamp) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (temp, water_level, ph, do, rpo, am ,timestamp))
        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

# 模拟数据生成并插入数据库
while True:
    temp = round(random.uniform(0.0, 100.0), 1)
    water_level = round(random.uniform(5, 20), 1)
    ph = round(random.uniform(0.0, 14.0), 1)
    do = round(random.uniform(0.0, 100.0), 1)
    rpo = round(random.uniform(0.0, 100.0), 1)
    am = round(random.uniform(0.0, 100.0), 1)
    insert_data(temp, water_level, ph, do,rpo,am)
    time.sleep(5)






