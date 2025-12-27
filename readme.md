# 📱 iPhone SMS Webhook Forwarder

一个私密、实时且持久化的 iPhone 短信转发工具。利用 iOS 快捷指令自动将短信推送到你专属的网页看板。

---

## ✨ 核心功能

- **🚀 零配置启动**：基于 Python Flask，即开即用。
- **🔒 隐私隔离**：首页一键生成专属 UUID，不同用户间的数据完全隔离，互不干扰。
- **⚡ 实时推送**：采用 WebSocket (Socket.IO) 技术，短信到达秒级推送到网页，无需手动刷新。

---

## 🛠️ 环境安装

1. **克隆项目或下载脚本**
2. **安装 Python 依赖库**：
```bash
pip install flask flask-socketio flask-limiter eventlet
```
3. **启动服务端**:
```bash
python app.py
```

默认运行地址：http://0.0.0.0:5000