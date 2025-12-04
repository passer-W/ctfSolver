from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import json
import os

db = SQLAlchemy()

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target = db.Column(db.String(255), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(50), nullable=False, default="pending")  # 任务状态: pending, running, finished
    is_running = db.Column(db.Boolean, nullable=False, default=False)  # 保留向后兼容
    flag = db.Column(db.String(255), nullable=False, default="")
    task_path = db.Column(db.String(500), nullable=True)  # 存储任务路径
    agent_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=True)  # 关联的Agent ID
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # 创建时间
    
    # 关联关系
    agent = db.relationship('Agent', backref=db.backref('tasks', lazy=True))
    
    def __init__(self, **kwargs):
        super(Task, self).__init__(**kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def explorered_pages(self):
        """动态获取探索的页面列表"""
        if self.task_path and os.path.exists(self.task_path):
            return os.listdir(self.task_path)
        return []
    
    def to_dict(self, include_messages=False):
        result = {
            'id': self.id,
            'target': self.target,
            'description': self.description,
            'status': self.status,
            'is_running': self.is_running,
            'flag': self.flag,
            'explorered_pages': self.explorered_pages,
            'pages_count': len(self.pages),
            'vulns_count': len(self.vulns),
            'agent_id': self.agent_id,
            'agent_name': self.agent.name if self.agent else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        # 如果需要包含消息，添加messages字段
        if include_messages:
            # 获取与此任务关联的消息（通过session_id = task_id）
            from models import Message
            messages = Message.query.filter_by(session_id=self.id).order_by(Message.created_at).all()
            result['messages'] = []
            
            for message in messages:
                message_dict = message.to_dict()
                # 为前端兼容性，添加messageType字段
                message_dict['messageType'] = message_dict['type']
                result['messages'].append(message_dict)
        
        return result

class Solution(db.Model):
    __tablename__ = 'solutions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = db.Column(db.String(100), nullable=False, default="漏洞类型")
    description = db.Column(db.Text, nullable=False, default="利用指导")
    result = db.Column(db.Text, nullable=False, default="利用结果")
    task_id = db.Column(db.String(36), db.ForeignKey('tasks.id'), nullable=True)
    
    # 关联关系
    task = db.relationship('Task', backref=db.backref('solutions', lazy=True))
    
    def __init__(self, **kwargs):
        super(Solution, self).__init__(**kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'description': self.description,
            'result': self.result,
            'task_id': self.task_id
        }

class Page(db.Model):
    __tablename__ = 'pages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False, default="")
    request = db.Column(db.Text, nullable=True)  # 存储JSON字符串
    response = db.Column(db.Text, nullable=True)  # 存储JSON字符串
    description = db.Column(db.Text, nullable=False, default="")
    key = db.Column(db.String(255), nullable=False, default="")
    discovered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # 发现时间
    task_id = db.Column(db.String(36), db.ForeignKey('tasks.id'), nullable=True)
    
    # 关联关系
    task = db.relationship('Task', backref=db.backref('pages', lazy=True))
    
    def __init__(self, **kwargs):
        super(Page, self).__init__(**kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def request_dict(self):
        """将request JSON字符串转换为字典"""
        if self.request:
            try:
                return json.loads(self.request)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @request_dict.setter
    def request_dict(self, value):
        """将字典转换为JSON字符串存储"""
        if value:
            self.request = json.dumps(value, ensure_ascii=False)
        else:
            self.request = None
    
    @property
    def response_dict(self):
        """将response JSON字符串转换为字典"""
        if self.response:
            try:
                return json.loads(self.response)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @response_dict.setter
    def response_dict(self, value):
        """将字典转换为JSON字符串存储"""
        if value:
            self.response = json.dumps(value, ensure_ascii=False)
        else:
            self.response = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'request': json.loads(self.request_dict),
            'response': json.loads(self.response_dict),
            'description': self.description,
            'key': self.key,
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None,
            'task_id': self.task_id
        }

class Vuln(db.Model):
    __tablename__ = 'vulns'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vuln_type = db.Column(db.String(100), nullable=False, default="")  # 漏洞类型
    severity = db.Column(db.String(50), nullable=False, default="MEDIUM")  # 严重程度: HIGH, MEDIUM, LOW
    description = db.Column(db.Text, nullable=False, default="")  # 漏洞描述
    request = db.Column(db.Text, nullable=True)  # 存储请求JSON字符串
    response = db.Column(db.Text, nullable=True)  # 存储响应JSON字符串
    discovered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # 发现时间
    task_id = db.Column(db.String(36), db.ForeignKey('tasks.id'), nullable=True)
    
    # 关联关系
    task = db.relationship('Task', backref=db.backref('vulns', lazy=True))
    
    def __init__(self, **kwargs):
        super(Vuln, self).__init__(**kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def request_dict(self):
        """将request JSON字符串转换为字典"""
        if self.request:
            try:
                return json.loads(self.request)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @request_dict.setter
    def request_dict(self, value):
        """将字典转换为JSON字符串存储"""
        if value:
            self.request = json.dumps(value, ensure_ascii=False)
        else:
            self.request = None
    
    @property
    def response_dict(self):
        """将response JSON字符串转换为字典"""
        if self.response:
            try:
                return json.loads(self.response)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @response_dict.setter
    def response_dict(self, value):
        """将字典转换为JSON字符串存储"""
        if value:
            self.response = json.dumps(value, ensure_ascii=False)
        else:
            self.response = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'vuln_type': self.vuln_type,
            'severity': self.severity,
            'description': self.description,
            'request': json.loads(self.request_dict),
            'response': json.loads(self.response_dict),
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None,
            'task_id': self.task_id
        }

class Message(db.Model):
    __tablename__ = 'messages'
    
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid.uuid4()))
    role = db.Column(db.String(50), nullable=False, default="")
    content = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(50), nullable=False, default="")
    type = db.Column(db.String(50), nullable=False, default="pure")  # 消息类型: pure, solution, page, summary, vulnerability, question
    msg_metadata = db.Column(db.Text, nullable=True)  # 存储JSON字符串，包含渲染所需的元数据
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # 添加与Task的关联关系 - 使用session_id作为task_id
    task_id = db.Column(db.String(36), db.ForeignKey('tasks.id'), nullable=True)
    task = db.relationship('Task', backref=db.backref('messages', lazy=True, order_by='Message.created_at'))
    
    def __init__(self, **kwargs):
        super(Message, self).__init__(**kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())
        # 如果session_id对应一个task_id，自动设置task_id
        if self.session_id and not self.task_id:
            from models import Task
            task = Task.query.get(self.session_id)
            if task:
                self.task_id = self.session_id

    @property
    def metadata_dict(self):
        """获取元数据字典"""
        if self.msg_metadata:
            try:
                return json.loads(self.msg_metadata)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @metadata_dict.setter
    def metadata_dict(self, value):
        """设置元数据字典"""
        if value is None:
            self.msg_metadata = None
        else:
            self.msg_metadata = json.dumps(value, ensure_ascii=False)
    
    def to_dict(self):
        # 处理metadata字段，确保返回字典格式
        metadata = None
        if self.msg_metadata:
            try:
                metadata = json.loads(self.msg_metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role,
            'content': self.content,
            'status': self.status,
            'type': self.type,
            'metadata': metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'timestamp': self.created_at.isoformat() if self.created_at else None  # 添加timestamp字段
        }

class Agent(db.Model):
    __tablename__ = 'agents'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False, default="")
    host = db.Column(db.String(255), nullable=False, default="")
    port = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(50), nullable=False, default="offline")
    capabilities = db.Column(db.Text, nullable=True)
    last_heartbeat = db.Column(db.DateTime, nullable=True)
    registered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, nullable=True)
    start_time = db.Column(db.DateTime, nullable=True)
    agent_metadata = db.Column(db.Text, nullable=True)
    
    def __init__(self, **kwargs):
        super(Agent, self).__init__(**kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def capabilities_dict(self):
        """获取能力字典"""
        if self.capabilities:
            try:
                return json.loads(self.capabilities)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @capabilities_dict.setter
    def capabilities_dict(self, value):
        """设置能力字典"""
        if value is not None:
            self.capabilities = json.dumps(value, ensure_ascii=False)
        else:
            self.capabilities = None
    
    @property
    def metadata_dict(self):
        """获取元数据字典"""
        if self.agent_metadata:
            try:
                return json.loads(self.agent_metadata)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @metadata_dict.setter
    def metadata_dict(self, value):
        """设置元数据字典"""
        if value is not None:
            self.agent_metadata = json.dumps(value, ensure_ascii=False)
        else:
            self.agent_metadata = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'status': self.status,
            'capabilities': self.capabilities_dict,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'registered_at': self.registered_at.isoformat() if self.registered_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'metadata': self.metadata_dict,
            'tasks_count': len(self.tasks) if hasattr(self, 'tasks') else 0
        }


class Log(db.Model):
    __tablename__ = 'logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = db.Column(db.String(255), nullable=False, default="")  # 日志标识token
    message = db.Column(db.Text, nullable=False, default="")  # 日志消息内容
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # 时间戳
    
    def __init__(self, **kwargs):
        super(Log, self).__init__(**kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def to_dict(self):
        return {
            'id': self.id,
            'token': self.token,
            'message': self.message,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class Process(db.Model):
    __tablename__ = 'processes'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = db.Column(db.String(50), nullable=False, default="pause")  # 允许值: run/pause
    addition = db.Column(db.Text, nullable=True)  # 额外信息
    
    def __init__(self, **kwargs):
        super(Process, self).__init__(**kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'addition': self.addition
        }

class History(db.Model):
    __tablename__ = 'histories'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    _metadata = db.Column(db.Text, nullable=True)  # 存储JSON字符串，包含所有历史信息
    process_id = db.Column(db.String(36), db.ForeignKey('processes.id'), nullable=False)  # 关联的Process ID
    process = db.relationship('Process', backref=db.backref('histories', lazy=True))

    def __init__(self, **kwargs):
        super(History, self).__init__(**kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def metadata_dict(self):
        """获取元数据字典"""
        if self._metadata:
            try:
                return json.loads(self._metadata)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    @metadata_dict.setter
    def metadata_dict(self, value):
        """设置元数据字典"""
        if value is not None:
            self._metadata = json.dumps(value, ensure_ascii=False)
        else:
            self._metadata = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'metadata': self.metadata_dict,
            'process_id': self.process_id
        }

def init_db(app):
    """初始化数据库"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print("数据库表创建成功！")

def drop_db(app):
    """删除数据库表"""
    db.init_app(app)
    with app.app_context():
        db.drop_all()
        print("数据库表删除成功！")