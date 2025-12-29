import eventlet
eventlet.monkey_patch()  # 必须写在最顶端，在导入 flask 和 socketio 之前
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, join_room
import datetime
import uuid
import sqlite3
import datetime
import uuid
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import config_env

app = Flask(__name__)
app.config['SECRET_KEY'] = config_env.app_securty_key
socketio = SocketIO(app, cors_allowed_origins="*")

limiter = Limiter(
    get_remote_address,  
    app=app,
    default_limits=["200 per day", "50 per hour"], 
    storage_uri="memory://", 
)

DB_FILE = config_env.dbname

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
                        (uuid TEXT PRIMARY KEY, created_at TIMESTAMP)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS messages 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         user_id TEXT, sender TEXT, content TEXT, time TEXT,
                         FOREIGN KEY(user_id) REFERENCES users(uuid))''')
        conn.commit()

init_db()

def add_new_user(user_id):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT INTO users (uuid, created_at) VALUES (?, ?)", 
                     (user_id, datetime.datetime.now()))
        conn.commit()

def save_message(user_id, sender, content, time_str):
    with sqlite3.connect(DB_FILE) as conn:
        count = conn.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,)).fetchone()[0]
        if count >= 50:
            conn.execute("DELETE FROM messages WHERE id IN (SELECT id FROM messages WHERE user_id = ? ORDER BY id ASC LIMIT 1)", (user_id,))
        conn.execute("INSERT INTO messages (user_id, sender, content, time) VALUES (?, ?, ?, ?)",
                     (user_id, sender, content, time_str))
        conn.commit()


@app.route('/')
def home():
    return render_template_string(HOME_TEMPLATE)


@app.route('/generate')
@limiter.limit("5 per hour") 
def generate():
    new_id = str(uuid.uuid4()).replace('-', '')[:16] 
    add_new_user(new_id)
    # 将 'dashboard' 改为 'unified_handler'
    return redirect(url_for('unified_handler', user_id=new_id))




HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>短信转发控制台</title>
    <style>
        body { font-family: system-ui; background: #f0f2f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .box { background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); max-width: 450px; text-align: center; }
        .btn { background: #007AFF; color: white; border: none; padding: 12px 24px; border-radius: 10px; font-size: 16px; cursor: pointer; transition: 0.2s; }
        .btn:hover { background: #0056b3; }
        h1 { margin-top: 0; font-size: 24px; }
        p { color: #666; font-size: 14px; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="box">
        <h1>🚀 欢迎使用短信转发器</h1>
        <p>点击下方按钮，生成一对专属的 <b>POST(发送)</b> 与 <b>GET(查看)</b> 地址。不同 ID 之间的数据完全隔离。</p>
        <button class="btn" onclick="window.location.href='/generate'">生成专属地址对</button>
    </div>
</body>
</html>
"""


DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>专属看板 - {{ user_id }}</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
        :root { --primary: #007AFF; --bg: #F2F2F7; --accent: #FF9500; }
        body { font-family: -apple-system, system-ui, sans-serif; background: var(--bg); margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .container { width: 100%; max-width: 500px; }
        
        /* 收藏提醒卡片 */
        .bookmark-tip { background: #FFF9E6; border: 1px dashed var(--accent); padding: 15px; border-radius: 12px; margin-bottom: 20px; display: flex; align-items: flex-start; gap: 10px; }
        .bookmark-tip span { font-size: 20px; }
        .bookmark-text { font-size: 13px; color: #856404; line-height: 1.5; }
        .bookmark-text b { color: #000; }

        .setup-card { background: #fff; padding: 20px; border-radius: 16px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .label { font-size: 11px; color: #888; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
        .url-box { background: #f8f8f8; padding: 10px; border-radius: 8px; font-family: monospace; font-size: 13px; margin-bottom: 15px; word-break: break-all; border: 1px solid #eee; color: #333; }
        .copy-btn { font-size: 10px; background: #eee; border: none; padding: 2px 6px; border-radius: 4px; cursor: pointer; color: var(--primary); }
        
        .card { background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 10px; animation: fadeIn 0.4s ease; border-left: 4px solid var(--primary); }
        .sender { color: var(--primary); font-weight: bold; font-size: 15px; }
        .time { float: right; color: #aaa; font-size: 12px; }
        .content { margin-top: 8px; font-size: 15px; color: #333; line-height: 1.4; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="bookmark-tip">
            <span>⭐️</span>
            <div class="bookmark-text">
                <b>重要提示：</b> 这是一个随机生成的临时私密地址。为了防止下次找不到，请立即 <b>Ctrl+D</b>（或点击浏览器星标）<b>收藏本页面</b> 到书签。
            </div>
        </div>

        <div class="setup-card">
            <h3 style="margin:0 0 15px 0">🔒 专属监控配置</h3>
            
            <div class="label">
                iPhone 填写的 POST 地址
                <button class="copy-btn" onclick="copyText('post-url')">复制地址</button>
            </div>
            <div class="url-box" id="post-url"></div>
            
            <div class="label">
                当前专属查看地址 (GET)
                <button class="copy-btn" onclick="copyText('get-url')">复制地址</button>
            </div>
            <div class="url-box" id="get-url"></div>
        </div>
        
        <div id="list">
            {% if not history %}
            <p style="text-align:center; color:#999; font-size:14px; margin-top:20px;">⏳ 等待 iPhone 发送短信...</p>
            {% endif %}
            {% for item in history %}
            <div class="card">
                <span class="sender">{{ item.sender }}</span>
                <span class="time">{{ item.time }}</span>
                <div class="content">{{ item.content }}</div>
            </div>
            {% endfor %}
        </div>
    </div>

    <script>
        const user_id = "{{ user_id }}";
        const base = window.location.origin;
        document.getElementById('post-url').innerText = window.location.href;
        document.getElementById('get-url').innerText = window.location.href;

        function copyText(id) {
            const text = document.getElementById(id).innerText;
            navigator.clipboard.writeText(text).then(() => alert('地址已复制'));
        }

        const socket = io();
        socket.on('connect', () => {
            socket.emit('join', { room: user_id });
        });

        socket.on('new_sms', function(data) {
            // 如果是第一条短信，清空等待提示
            const emptyTip = document.querySelector('#list p');
            if (emptyTip) emptyTip.remove();

            const html = `
                <div class="card">
                    <span class="sender">${data.sender}</span>
                    <span class="time">${data.time}</span>
                    <div class="content">${data.content}</div>
                </div>`;
            document.getElementById('list').insertAdjacentHTML('afterbegin', html);
        });
    </script>
</body>
</html>
"""

@app.route('/sms/<user_id>', methods=['POST'])
@app.route('/<user_id>', methods=['GET', 'POST']) # 这里必须包含 GET
@limiter.limit("30 per minute") 
def unified_handler(user_id):
    # 1. 验证用户是否存在
    with sqlite3.connect(DB_FILE) as conn:
        user = conn.execute("SELECT uuid FROM users WHERE uuid = ?", (user_id,)).fetchone()
    if not user:
        return "地址无效或已过期", 404

    # 2. 如果是 GET 请求：返回看板页面 (原 dashboard 逻辑)
    if request.method == 'GET':
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.execute("SELECT sender, content, time FROM messages WHERE user_id = ? ORDER BY id DESC", (user_id,))
            history = [{"sender": r[0], "content": r[1], "time": r[2]} for r in cursor.fetchall()]
        return render_template_string(DASHBOARD_TEMPLATE, user_id=user_id, history=history)

    # 3. 如果是 POST 请求：保存短信 (原 receive_sms 逻辑)
    data = request.json
    if not data or 'content' not in data:
        return jsonify({"status": "invalid_data"}), 400

    new_entry = {
        "time": datetime.datetime.now().strftime('%H:%M:%S'),
        "sender": data.get('sender', '未知'),
        "content": data.get('content', '')
    }
    
    save_message(user_id, new_entry['sender'], new_entry['content'], new_entry['time'])
    socketio.emit('new_sms', new_entry, room=user_id)
    return jsonify({"status": "ok"}), 200

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "请求太频繁了，请稍后再试", "message": str(e.description)}), 429

@socketio.on('join')
def on_join(data):
    join_room(data['room'])

if __name__ == '__main__':
    print("服务器正在通过 eventlet 启动，运行在 http://0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
