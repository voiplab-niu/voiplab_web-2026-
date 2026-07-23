# app.py（前面就這些，不要中間再 import Flask）
import datetime
import os
import re
import uuid
import random
import json
import sqlite3
import base64      # 只用於其他 route
import subprocess  # Celery task 裡用
import pymysql

from flask import (
    Flask, jsonify, render_template, request, redirect, url_for,
    session, Response, abort, send_from_directory, send_file, make_response
)
from functools import wraps
import requests
from werkzeug.middleware.proxy_fix import ProxyFix
from urllib.parse import urlencode  # 新增这行
from authlib.integrations.flask_client import OAuth  # 新增这行
from authlib.common.security import generate_token

# 下面這兩行，用於排 background job
from tasks import process_video

app = Flask(__name__, static_url_path='/fish_farm/static')
app.secret_key = '1234'  # 必須設置且保密
app.config.update(
    SESSION_COOKIE_SECURE=False,    # 僅允許 HTTPS 傳輸 Cookie
    SESSION_COOKIE_HTTPONLY=True,  # 防止 JavaScript 訪問 Cookie
    SESSION_COOKIE_SAMESITE='Lax'  # 防止 CSRF
)
app.config['APPLICATION_ROOT'] = '/fish_farm'
app.config['GOOGLE_CLIENT_ID'] = '428735946048-qqlrgaeasddbrj0jfbcko3u0kka09jm6.apps.googleusercontent.com'
app.config['GOOGLE_CLIENT_SECRET'] = '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'
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',  # 关键修正
    client_kwargs={
        'scope': 'openid email profile',
        'nonce': True  # 启用 nonce 支持
    }
)



app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_prefix=1)  # 增加 x_prefix 支援


# 用戶資料庫
users = {'jason': '121212', 'rrrr': '114514'}

# Webhook 設定
WEBHOOK_URL = "https://niuo365.webhook.office.com/webhookb2/0486203e-905e-4f27-956f-4e77fadc7f1d@6614bde6-0eb1-4cbf-a4f4-bdc5ed185995/IncomingWebhook/e8fa1898d8974683864b2e5ff2325fda/2f6de259-56d5-4a74-b4d1-7cec560bb92b/V2N7bztmrG29etgYBjH_nasvDh-XwWbZy06V854TonDO01"
LINE_NOTIFY_TOKEN = "8LCibtpxccr13fPPya0bCMO7wXd57hakBqqIgMh6avE"

# 警報狀態追蹤
alert_feedback_status = {"0423-7537": {"status": "未處理"}}


def send_teams_notification(alert_id, alert_type, alert_content):
    """
    发送 Teams 通知，包含频率限制和状态检查
    
    参数:
        alert_id: 警报唯一ID
        alert_type: 警报类型 (如"水质异常")
        alert_content: 警报详细内容
    
    返回:
        tuple: (success: bool, message: str)
    """
    conn = None
    try:
        conn = get_mysql_connection()
        
        with conn.cursor() as cursor:
            # 1. 获取当前警报状态
            cursor.execute("""
                SELECT status, notification_count, last_notified_time 
                FROM abnormal_events 
                WHERE web_id = %s
                FOR UPDATE  # 加锁防止并发问题
            """, (alert_id,))
            alert = cursor.fetchone()

            if not alert:
                logging.warning(f"警报不存在: {alert_id}")
                return False, "找不到警报记录"

            # 2. 状态检查
            if alert['status'] != '未處理':
                logging.info(f"警报 {alert_id} 状态已变更为 {alert['status']}，跳过通知")
                return False, f"状态已变更为 {alert['status']}"

            # 3. 频率限制检查
            current_time = datetime.now()
            min_interval = timedelta(minutes=10)  # 最小间隔10分钟
            
            if alert['last_notified_time']:
                time_since_last = current_time - alert['last_notified_time']
                if time_since_last < min_interval:
                    logging.debug(f"警报 {alert_id} 通知间隔 {time_since_last} 小于最小间隔 {min_interval}")
                    return False, "通知间隔过短"

            # 4. 通知次数限制
            max_notifications = 10
            if alert['notification_count'] >= max_notifications:
                logging.warning(f"警报 {alert_id} 已达到最大通知次数 {max_notifications}")
                return False, "已达通知上限"

            # 5. 准备通知消息
            message = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "FF0000",
                "summary": f"鱼池监控系统警报 - {alert_type}",
                "sections": [{
                    "activityTitle": "🐟 **鱼池监控系统警报**",
                    "activitySubtitle": f"**类型**: {alert_type}",
                    "facts": [
                        {"name": "时间", "value": current_time.strftime("%Y-%m-%d %H:%M:%S")},
                        {"name": "内容", "value": alert_content},
                        {"name": "警报ID", "value": alert_id}
                    ],
                    "markdown": True
                }],
                "potentialAction": [{
                    "@type": "OpenUri",
                    "name": "立即处理",
                    "targets": [{
                        "os": "default",
                        "uri": f"https://voiplab.niu.edu.tw/fish_farm/confirm_alert/{alert_id}"
                    }]
                }]
            }

            # 6. 发送通知
            response = requests.post(
                WEBHOOK_URL,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            response.raise_for_status()

            # 7. 更新数据库记录
            cursor.execute("""
                UPDATE abnormal_events 
                SET last_notified_time = %s,
                    notification_count = notification_count + 1
                WHERE web_id = %s
            """, (current_time, alert_id))
            conn.commit()

            logging.info(f"成功发送警报通知: {alert_id}")
            return True, "发送成功"

    except requests.exceptions.RequestException as e:
        logging.error(f"Teams 通知发送失败: {str(e)}")
        return False, f"网络错误: {str(e)}"
    except pymysql.Error as db_err:
        logging.error(f"数据库操作失败: {str(db_err)}")
        if conn:
            conn.rollback()
        return False, "数据库错误"
    except Exception as e:
        logging.error(f"未知错误: {str(e)}")
        return False, "服务器内部错误"
    finally:
        if conn:
            conn.close()

# 登入檢查裝飾器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 排除靜態文件、API路由和登入頁面
        excluded_paths = [
            '/fish_farm/static/',
            '/fish_farm/api/',
            '/fish_farm/login',
            '/fish_farm/login/callback',
            '/fish_farm/confirm_alert/',
            '/fish_farm/process_alert/'
        ]
        if any(request.path.startswith(path) for path in excluded_paths):
            return f(*args, **kwargs)
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/fish_farm/logout')
def logout():
    # 清除 session
    session.clear()
    # 重定向到登录页面
    return redirect(url_for('login'))

@app.route('/fish_farm/static/videos/<path:filename>')
def serve_video(filename):
    video_dir = os.path.join(app.root_path, 'static', 'videos')
    video_path = os.path.join(video_dir, filename)
    
    if not os.path.exists(video_path):
        abort(404)
    
    # 检查文件扩展名
    if not filename.lower().endswith('.mp4'):
        abort(400, description="只支持MP4格式视频")
    
    # 获取文件大小
    file_size = os.path.getsize(video_path)
    
    # 处理范围请求
    range_header = request.headers.get('Range', None)
    if range_header:
        # 解析范围请求
        byte1, byte2 = 0, None
        m = re.search(r'(\d+)-(\d*)', range_header)
        if m:
            groups = m.groups()
            byte1 = int(groups[0])
            if groups[1]:
                byte2 = int(groups[1])
        
        length = (byte2 + 1 if byte2 is not None else file_size) - byte1
        
        # 读取部分文件内容
        with open(video_path, 'rb') as f:
            f.seek(byte1)
            data = f.read(length)
        
        # 构建部分响应
        resp = Response(
            data,
            206,
            mimetype='video/mp4',
            direct_passthrough=True
        )
        resp.headers.add('Content-Range', f'bytes {byte1}-{byte1 + length - 1}/{file_size}')
    else:
        # 完整文件响应
        resp = send_file(video_path, mimetype='video/mp4')
    
    # 设置通用响应头
    resp.headers.add('Accept-Ranges', 'bytes')
    resp.headers.add('Content-Length', str(file_size))
    resp.headers.add('Cache-Control', 'no-cache')
    
    return resp
def handle_range_request(video_path):
    file_size = os.path.getsize(video_path)
    start, end = 0, file_size - 1
    
    range_header = request.headers.get('Range')
    if range_header:
        ranges = range_header.strip().split('=')
        if len(ranges) == 2 and ranges[0] == 'bytes':
            byte_ranges = ranges[1].split('-')
            try:
                start = int(byte_ranges[0]) if byte_ranges[0] else 0
                end = int(byte_ranges[1]) if byte_ranges[1] else file_size - 1
            except ValueError:
                pass
    
    length = end - start + 1
    with open(video_path, 'rb') as f:
        f.seek(start)
        data = f.read(length)
    
    response = Response(
        data,
        206,
        mimetype='video/mp4',
        direct_passthrough=True
    )
    
    response.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
    response.headers.add('Accept-Ranges', 'bytes')
    response.headers.add('Content-Length', str(length))
    response.headers.add('Cache-Control', 'public, max-age=3600')
    
    return response

# 登入路由
@app.route('/fish_farm/login', methods=['GET'])
def login():
    # 若有錯誤訊息就顯示，否則為 None
    error = request.args.get('error')
    return render_template('login.html', error=error)
# 处理账号密码登录
@app.route('/fish_farm/login', methods=['POST'])
def local_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if users.get(username) == password:
        session['logged_in'] = True
        session['username'] = username
        return redirect(url_for('index'))
    else:
        return redirect(url_for('login', error='帳號或密碼錯誤'))
@app.route('/fish_farm/login/google')
def google_login():
    nonce = generate_token(20)
    session['oauth_nonce'] = nonce
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(
        redirect_uri=redirect_uri,
        nonce=nonce
    )

    
@app.route('/fish_farm/login/callback')
def authorize():
    try:
        token = google.authorize_access_token()
        
        # 从 Session 获取并删除 nonce
        nonce = session.pop('oauth_nonce', None)
        if not nonce:
            abort(400, "Missing nonce")

        # 验证 nonce
        userinfo = google.parse_id_token(token, nonce=nonce)  # 传入 nonce

        # 设置 Session
        session['logged_in'] = True
        session['google_user'] = {
            'email': userinfo['email'],
            'name': userinfo.get('name'),
            'picture': userinfo.get('picture')
        }
        return redirect(url_for('index'))

    except Exception as e:
        logging.error(f"OAuth 登录失败: {str(e)}")
        # 清除无效 Session
        session.clear()
        return redirect(url_for('login', error='login_failed'))
# 需要登入的路由
@app.route('/fish_farm/')
@login_required
def index():
    return render_template('index.html')

@app.route('/fish_farm/test')
@login_required
def test():
    return render_template('test.html')

@app.route('/fish_farm/line.html')
@login_required
def line():
    return render_template('line.html')

@app.route('/fish_farm/fish1.html')
@login_required
def fish1():
    return render_template('fish1.html')

@app.route('/fish_farm/fish2.html')
@login_required
def fish2():
    return render_template('fish2.html')

@app.route('/fish_farm/fish3.html')
@login_required
def fish3():
    return render_template('fish3.html')

@app.route('/fish_farm/aichat.html')
@login_required
def aichat():
    return render_template('aichat.html')

@app.route('/fish_farm/alertSettings.html')
@login_required
def alertSettings():
    return render_template('alertSettings.html')
from flask import current_app
import traceback
# API路由
import logging
from datetime import datetime
from authlib.integrations.flask_client import OAuth


# 在應用程式初始化後添加
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='fish_farm.log'
)

@app.route('/fish_farm/api/abnormal-events', methods=['GET'])
def get_abnormal_events():
    conn = None
    try:
        pond_id = request.args.get('pond_id')  # 新增參數
        
        # 初始化基本查詢
        base_query = """
            SELECT web_id, type, content, flip_time, status
            FROM abnormal_events
            ORDER BY flip_time DESC
        """
        
        # 檢查連接是否可用
        conn = get_mysql_connection()
        if not conn:
            logging.error("無法建立資料庫連接")
            return jsonify([])
            
        with conn.cursor() as cursor:
            # 如果有pond_id參數，添加過濾條件
            if pond_id:
                base_query += " WHERE web_id LIKE %s"
                param = f"%-{pond_id}_"  # 使用 _ 作為單字符通配符
                cursor.execute(base_query, (param,))
            else:
                cursor.execute(base_query)
                
            alerts = cursor.fetchall()
            
            # 加上影片 URL
            for alert in alerts:
                alert['video_url'] = f"/fish_farm/static/videos/{alert['web_id']}.mp4"
                # 確保 flip_time 是字符串格式
                if isinstance(alert['flip_time'], datetime):
                    alert['flip_time'] = alert['flip_time'].strftime('%Y-%m-%d %H:%M:%S')
            logging.info(f"成功獲取 {len(alerts)} 筆異常事件")
            return jsonify(alerts)
            
    except Exception as e:
        logging.error(f"獲取異常事件失敗: {str(e)}\n{traceback.format_exc()}")
        return jsonify([])
        
    finally:
        if conn:
            conn.close()
@app.route('/fish_farm/send_notify', methods=['POST'])
@app.route('/fish_farm/send_notify', methods=['POST'])
def send_notify():
    """简化版通知接口（最多处理3次）"""
    try:
        data = request.get_json()
        alert_id = data.get('alertId', '').strip()
        attempt = int(data.get('attempt', 1))
        
        # 1. 基础验证
        if not alert_id or attempt > 3:
            return jsonify({
                'success': False,
                'error': 'Invalid request',
                'stopRetry': True  # 永久停止
            }), 400

        # 2. 模拟成功响应（实际项目需添加真实发送逻辑）
        return jsonify({
            'success': True,
            'message': f'Notification #{attempt} sent',
            'alert_id': alert_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'stopRetry': attempt >= 3  # 第3次失败后停止
        }), 500





@app.route('/fish_farm/get_alert_feedback')
def get_alert_feedback():
    # 回傳所有警報的狀態 (JSON)
    return jsonify(alert_feedback_status)




def get_db_connection():
    conn = sqlite3.connect('alert.db')  # 使用你的 SQLite 檔名
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/fish_farm/save-alert', methods=['POST'])
def save_alert():
    data = request.get_json()
    
    # 獲取所有要儲存的值
    temp_min = data.get('tempMin')
    temp_max = data.get('tempMax')
    ph_min = data.get('pHMin')
    ph_max = data.get('pHMax')
    do_min = data.get('doMin')
    do_max = data.get('doMax')
    orp_min = data.get('orpMin')
    orp_max = data.get('orpMax')
    salt_min = data.get('saltMin')
    salt_max = data.get('saltMax')

    # 獲取當前時間
    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        # 儲存到 SQLite 數據庫
        conn = sqlite3.connect('/var/www/voiplab.niu.edu.tw/fish_farm_web/alert2.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alert 
            (temp_min, temp_max, ph_min, ph_max, do_min, do_max, orp_min, orp_max, salt_min, salt_max, time) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
            (temp_min, temp_max, ph_min, ph_max, do_min, do_max, orp_min, orp_max, salt_min, salt_max, time))
        conn.commit()
    except Exception as e:
        return jsonify({'error': str(e)}), 500  # 返回錯誤信息
    finally:
        # 確保連接和光標關閉
        cursor.close()
        conn.close()

    return jsonify({'message': '異常值已儲存'}), 201
@app.route('/fish_farm/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    conn = None
    try:
        # ----- 1. 记录原始请求数据 -----
        raw_data = request.get_data(as_text=True)
        logging.info(f"原始请求数据: {raw_data}")

        # ----- 2. 解析 JSON -----
        data = request.get_json()
        if not data:
            logging.error("空请求体")
            return jsonify({"error": "请求体不能为空"}), 400
        logging.info(f"解析后的 JSON 数据: {data}")

        # ----- 3. 强制字段检查 -----
        required_fields = ['pond_id', 'temperature', 'ph', 'do', 'orp', 'salt', 'timestamp']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            logging.error(f"缺失字段: {missing_fields}")
            return jsonify({"error": f"缺失必要字段: {missing_fields}"}), 400
        logging.info("字段完整性验证通过")

        # ----- 4. 数据类型转换 -----
        try:
            # 处理时间戳（允许带毫秒）
            raw_timestamp = data['timestamp']
            if '.' in raw_timestamp:
                # 分割日期和毫秒部分
                timestamp_str, _ = raw_timestamp.split('.', 1)
            else:
                timestamp_str = raw_timestamp

            sensor_data = {
                'pond_id': int(data['pond_id']),
                'temperature': float(data['temperature']),
                'ph': float(data['ph']),
                'do': float(data['do']),
                'orp': float(data['orp']),
                'salt': float(data['salt']),
                'timestamp': datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
            }
            flip_time_str = timestamp_str  # 格式: "YYYY-MM-DD HH:MM:SS"

        except (ValueError, TypeError) as e:
            logging.error(f"数据类型错误: {str(e)}")
            return jsonify({"error": "数据类型转换失败"}), 400
        logging.info(f"转换后的传感器数据: {sensor_data}")

        # ----- 5. 获取阈值配置 -----
        threshold_response = get_alert_thresholds()
        if threshold_response.status_code != 200:
            logging.error("取得閾值設定失敗")
            return jsonify({"error": "無法取得警戒閾值"}), 500

        thresholds = threshold_response.get_json()
        if not thresholds:
            logging.error("获取阈值配置失败")
            return jsonify({"error": "服务器配置错误"}), 500
        logging.info(f"当前阈值配置: {thresholds}")

      

        # ----- 7. 异常检测逻辑 -----
        alert_messages = []
        # 温度检测
        if sensor_data['temperature'] < thresholds['temp_Min']:
            alert_messages.append(f"溫度過低: {sensor_data['temperature']}°C (最低阈值 {thresholds['temp_Min']}°C)")
        elif sensor_data['temperature'] > thresholds['temp_Max']:
            alert_messages.append(f"溫度過高: {sensor_data['temperature']}°C (最高阈值 {thresholds['temp_Max']}°C)")

        elif sensor_data['ph'] < thresholds['phMin']:
            alert_messages.append(f"ph過低: {sensor_data['ph']} (最低阈值 {thresholds['phMin']})")
        elif sensor_data['ph'] > thresholds['phMax']:
            alert_messages.append(f"ph過高: {sensor_data['ph']} (最高阈值 {thresholds['phMax']})")

        elif sensor_data['do'] < thresholds['doMin']:
            alert_messages.append(f"溶氧過低: {sensor_data['do']}mg/L (最低阈值 {thresholds['doMin']}mg/L)")
        elif sensor_data['do'] > thresholds['doMax']:
            alert_messages.append(f"溶氧過高: {sensor_data['do']}mg/L (最高阈值 {thresholds['doMax']}mg/L)")

        elif sensor_data['orp'] < thresholds['orpMin']:
            alert_messages.append(f"氧化還原電位過低: {sensor_data['orp']}mV (最低阈值 {thresholds['orpMin']}mV)")
        elif sensor_data['orp'] > thresholds['orpMax']:
            alert_messages.append(f"氧化還原電位過低高: {sensor_data['orp']}mV (最高阈值 {thresholds['orpMax']}mV)")

        elif sensor_data['salt'] < thresholds['saltMin']:
            alert_messages.append(f"鹽度過低: {sensor_data['salt']}PSU (最低阈值 {thresholds['saltMin']}PSU)")
        elif sensor_data['salt'] > thresholds['saltMax']:
            alert_messages.append(f"鹽度過高: {sensor_data['salt']}PSU (最高阈值 {thresholds['saltMax']}PSU)")
        
     
         

        if not alert_messages:
            logging.info("水质参数正常，无需记录异常")
            return jsonify({"message": "数据接收成功，无异常"}), 200

        logging.info(f"检测到异常: {alert_messages}")

        # ----- 8. 数据库操作 -----
        conn = get_mysql_connection()
        if not conn:
            logging.error("数据库连接失败")
            return jsonify({"error": "无法连接数据库"}), 500

        with conn.cursor() as cursor:
            alert_id = sensor_data['timestamp'].strftime('%m%d-%H%M%S') + f"-{sensor_data['pond_id']}1"
            logging.info(f"生成的警报ID: {alert_id}")

            # 检查30分钟内是否已有相同警报
            check_query = """
                SELECT COUNT(*) 
                FROM abnormal_events 
                WHERE flip_time > NOW() - INTERVAL 30 MINUTE
            """
            cursor.execute(check_query)
            result = cursor.fetchone()
            count = result['COUNT(*)'] if result else 0
            logging.info(f"重复警报检查结果: {count} 条记录")

            if count == 0:
                insert_query = """
                INSERT INTO abnormal_events 
                (web_id, type, content, flip_time, status)
                VALUES (%s, %s, %s, %s, %s)
                """
                insert_params = (
                    alert_id,                    # web_id (varchar30)
                    '水質異常',                   # type (varchar50)
                    '，'.join(alert_messages),    # content (text)
                    sensor_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),  # flip_time (varchar19)
                    '未處理',                     # status (varchar20)
                )
                logging.info(f"即將執行插入語句: {insert_query} with {insert_params}")
                try:        
                    cursor.execute(insert_query, insert_params)
                    conn.commit()
                    logging.info(f"数据插入成功，警报ID: {alert_id}")
                except pymysql.Error as e:
                    logging.error(f"數據庫插入失敗: {str(e)}")
                    conn.rollback()
                # 发送通知...
            else:
                logging.info("30分钟内已有相同警报，跳过插入")

        return jsonify({"alert_id": alert_id, "message": "异常已记录"}), 201

    except pymysql.Error as dberr:
        logging.error(f"数据库错误: {str(dberr)}")
        if conn:
            conn.rollback()
        return jsonify({"error": "数据库操作异常"}), 500
    except Exception as e:
        logging.error(f"未处理异常: {traceback.format_exc()}")
        return jsonify({"error": "服务器内部错误"}), 500
    finally:
        if conn:
            conn.close()
@app.route('/fish_farm/get-alert-thresholds', methods=['GET'])
def get_alert_thresholds():
    try:
        conn = sqlite3.connect('/var/www/voiplab.niu.edu.tw/fish_farm_web/alert2.db')  # 获取数据库连接
        cursor = conn.cursor() 

        # SQL 查詢，按時間排序，限制返回 1 條記錄
        cursor.execute("""
            SELECT temp_min, temp_max, ph_min, ph_max, do_min, do_max, orp_min, orp_max, salt_min, salt_max, time 
            FROM alert 
            ORDER BY time DESC LIMIT 1;
        """)
        thresholds = cursor.fetchone()

        # 確認查詢是否返回了資料
        if thresholds:
            return jsonify({
                'temp_Min': thresholds[0],
                'temp_Max': thresholds[1],
                'phMin': thresholds[2],
                'phMax': thresholds[3],
                'doMin': thresholds[4],
                'doMax': thresholds[5],
                'orpMin': thresholds[6],
                'orpMax': thresholds[7],
                'saltMin': thresholds[8],
                'saltMax': thresholds[9],
                'time': thresholds[10]
            })
        else:
            return jsonify({'error': 'No thresholds found'}), 404

    except sqlite3.DatabaseError as db_error:
        return jsonify({'error': f'Database error: {str(db_error)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()








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
        
        return connection
    except Exception as e:
        print("Connection failed:", e)
        raise  # 重新拋出錯誤
    



@app.route("/fish_farm/get_status", methods=['GET'])
def get_status():
    pond = request.args.get('pond', type=int)  # 從查詢參數獲取 pond
    connection = None
    try:
        connection = get_mysql_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT status FROM abnormal_events
                WHERE SUBSTRING(web_id, -2, 1) = %s
                  AND type = '行為異常'
                  AND content = '異常翻身'
                ORDER BY timestamp DESC
                LIMIT 1
            """
            cursor.execute(sql, (str(pond),))
            result = cursor.fetchone()
            
            
            if result:
                return jsonify({"status": result["status"]})
            else:
                return jsonify({"status": "正常"})
                
    except Exception as e:
        print("Database error:", e)
        return jsonify({"status": "錯誤"}), 500
    finally:
        if connection:
            connection.close()

# 1️⃣ 確認頁面路由：更新 received_notification_time、status → 已通知
@app.route('/fish_farm/confirm_alert/<alert_id>')
def confirm_alert(alert_id):
    print(f"收到確認請求: {alert_id}")

    # 安全地更新 in-memory 狀態（避免 KeyError）
    if alert_id in alert_feedback_status:
        alert_feedback_status[alert_id]['status'] = '已通知'
    else:
        print(f"警告：alert_feedback_status 中找不到 {alert_id}")

    # 同步寫入資料庫
    conn = get_mysql_connection()
    with conn.cursor() as cursor:
        sql = """
            UPDATE abnormal_events
               SET received_notification_time = NOW(),
                   status = '已通知'
             WHERE web_id = %s
        """
        cursor.execute(sql, (alert_id,))
    conn.commit()
    conn.close()

    return render_template("confirm_alert.html", alert_id=alert_id)


# 2️⃣ 已處理按鈕 POST 路由：更新 process_time、status → 已處理，並導回首頁
@app.route('/fish_farm/process_alert/<alert_id>', methods=['POST'])
def process_alert(alert_id):
    # 更新 in-memory
    alert_feedback_status.setdefault(alert_id, {})
    alert_feedback_status[alert_id]['status'] = '已處理'

    # 寫入資料庫
    conn = get_mysql_connection()
    with conn.cursor() as cursor:
        sql = """
          UPDATE abnormal_events
             SET process_time = NOW(),
                 status = '已處理'
           WHERE web_id = %s
        """
        cursor.execute(sql, (alert_id,))
    conn.commit()
    conn.close()

    # 處理完，跳回魚池首頁
    return redirect(url_for('fish1'))

from threading import Thread
import time

def background_scheduler():
    """背景定時任務檢查未處理警報"""
    while True:
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                # 查詢需要通知的警報
                cursor.execute("""
                    SELECT web_id, type, content 
                    FROM abnormal_events 
                    WHERE status = '未處理'
                      AND (last_notified_time IS NULL 
                           OR TIMESTAMPDIFF(SECOND, last_notified_time, NOW()) >= 10)
                    
                """)
                alerts = cursor.fetchall()
                
                for alert in alerts:
                    send_teams_notification(
                        alert_id=alert['web_id'],
                        alert_type=alert['type'],
                        alert_content=alert['content']
                    )
                    
            time.sleep(10)  # 10秒檢查間隔
        except Exception as e:
            logging.error(f"定時任務錯誤: {str(e)}")
            time.sleep(60)  # 錯誤後延長等待
import logging

# 配置日志记录
logging.basicConfig(
    level=logging.DEBUG,  # 设置为 DEBUG 级别以捕获所有信息
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='flask_debug.log'  # 日志保存到文件
)

# 启用 Werkzeug 的日志（Flask 底层服务器）
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.DEBUG)

# 在應用啟動時啟動定時任務
if __name__ == '__main__':
    # 確保靜態文件目錄存在
    os.makedirs(os.path.join(app.root_path, 'static', 'videos'), exist_ok=True)
    
    # 生產環境應設置 debug=False
    app.run(host='0.0.0.0', port=5000, debug=True)




