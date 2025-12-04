from flask import Flask
from flask_cors import CORS
from models import db, init_db
from controllers.task_controller import task_bp
from controllers.vuln_controller import vuln_bp
from controllers.page_controller import page_bp
from controllers.agent_controller import agent_bp
from controllers.message_controller import message_bp
from controllers.process_controller import process_bp
from celery_config import make_celery

app = Flask(__name__)

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ctf_tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Celery配置
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# 启用CORS支持前端跨域请求
CORS(app)

# 初始化Celery
celery = make_celery(app)

# 初始化数据库 - 只调用一次init_db即可
init_db(app)

# 注册蓝图
app.register_blueprint(task_bp)
app.register_blueprint(vuln_bp)
app.register_blueprint(page_bp)
app.register_blueprint(agent_bp)
app.register_blueprint(message_bp)
app.register_blueprint(process_bp)

@app.route('/')
def hello_world():
    return 'CTF Task Management API is running!'

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'message': 'API is running'}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
