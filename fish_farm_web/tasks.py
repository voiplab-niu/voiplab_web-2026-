import os
import base64
import subprocess
import pymysql
from celery_app import celery

def get_mysql_connection():
    try:
        connection = pymysql.connect(
            host='203.145.207.46',
            user='web',
            password='voiplab168',
            database='error_test',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("Database connected")
        return connection
    except Exception as e:
        print("Connection failed:", e)
        raise  # 重新拋出錯誤


@celery.task
def process_video(web_id, base64_data, static_folder):
    try:
        # 确保路径正确
        video_dir = os.path.join(static_folder, 'videos')
        os.makedirs(video_dir, exist_ok=True)
        video_path = os.path.join(video_dir, f'{web_id}-fast.mp4')
        
        # 保存视频文件
        mp4_data = base64.b64decode(base64_data.split(',')[1])
        with open(video_path, 'wb') as f:
            f.write(mp4_data)
        
        # 更新数据库
        video_url = f'/fish_farm/static/videos/{web_id}-fast.mp4'  # 确保路径前缀正确
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE abnormal_events
                SET formatted_time_url = %s,
                    video_status = 'ready'
                WHERE web_id = %s
            """, (video_url, web_id))
            conn.commit()
        return video_path
    
    except Exception as e:
        print(f"[❌ 處理失敗] {e}")
        # 更新狀態為失敗
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE abnormal_events
                   SET video_status = 'failed'
                 WHERE web_id = %s
            """, (web_id,))
            conn.commit()
        raise
    finally:
        if conn:
            conn.close()
