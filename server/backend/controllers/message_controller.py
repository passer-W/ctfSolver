from flask import Blueprint, request, jsonify
from models import db, Message, Task
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import uuid

message_bp = Blueprint('message', __name__, url_prefix='/api/messages')

@message_bp.route('', methods=['GET'])
def get_messages():
    """获取所有消息"""
    try:
        # 支持按session_id过滤
        session_id = request.args.get('session_id')
        task_id = request.args.get('task_id')
        
        query = Message.query
        
        if session_id:
            query = query.filter_by(session_id=session_id)
        
        if task_id:
            # 如果指定了task_id，使用task_id作为session_id
            query = query.filter_by(session_id=task_id)
        
        messages = query.order_by(Message.created_at.asc()).all()
        
        return jsonify({
            'success': True,
            'data': [message.to_dict() for message in messages],
            'message': '获取消息列表成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取消息列表失败: {str(e)}'
        }), 500

@message_bp.route('/<message_id>', methods=['GET'])
def get_message(message_id):
    """根据ID获取单个消息"""
    try:
        message = Message.query.get(message_id)
        if not message:
            return jsonify({
                'success': False,
                'message': '消息不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': message.to_dict(),
            'message': '获取消息成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取消息失败: {str(e)}'
        }), 500

@message_bp.route('', methods=['POST'])
def create_message():
    """创建新消息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        # 验证必需字段
        required_fields = ['session_id', 'role', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必需字段: {field}'
                }), 400
        
        
        
        message = Message(
            session_id=data['session_id'],
            role=data['role'],
            content=data['content'],
            status=data.get('status', ''),
            type=data.get('type', 'pure')
        )
        
        # 设置元数据
        if 'metadata' in data:
            message.metadata_dict = data['metadata']
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': message.to_dict(),
            'message': '消息创建成功'
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '消息创建失败：数据完整性错误'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'消息创建失败: {str(e)}'
        }), 500

@message_bp.route('/<message_id>', methods=['PUT'])
def update_message(message_id):
    """更新消息"""
    try:
        message = Message.query.get(message_id)
        if not message:
            return jsonify({
                'success': False,
                'message': '消息不存在'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        # 更新消息字段
        if 'session_id' in data:
            message.session_id = data['session_id']
        if 'role' in data:
            message.role = data['role']
        if 'content' in data:
            message.content = data['content']
        if 'status' in data:
            message.status = data['status']
        if 'type' in data:
            message.type = data['type']
        if 'metadata' in data:
            message.metadata_dict = data['metadata']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': message.to_dict(),
            'message': '消息更新成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'消息更新失败: {str(e)}'
        }), 500

@message_bp.route('/<message_id>', methods=['DELETE'])
def delete_message(message_id):
    """删除消息"""
    try:
        message = Message.query.get(message_id)
        if not message:
            return jsonify({
                'success': False,
                'message': '消息不存在'
            }), 404
        
        db.session.delete(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '消息删除成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'消息删除失败: {str(e)}'
        }), 500

@message_bp.route('/session/<session_id>', methods=['DELETE'])
def delete_session_messages(session_id):
    """删除指定会话的所有消息"""
    try:
        messages = Message.query.filter_by(session_id=session_id).all()
        
        for message in messages:
            db.session.delete(message)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'会话 {session_id} 的所有消息已删除'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除会话消息失败: {str(e)}'
        }), 500

@message_bp.route('/task/<task_id>', methods=['GET'])
def get_task_messages(task_id):
    """获取指定任务的所有消息"""
    try:
        # 验证任务是否存在
        task = Task.query.get(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404
        
        # 使用task_id作为session_id查询消息
        messages = Message.query.filter_by(session_id=task_id).order_by(Message.created_at.asc()).all()
        
        return jsonify({
            'success': True,
            'data': [message.to_dict() for message in messages],
            'message': '获取任务消息成功'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取任务消息失败: {str(e)}'
        }), 500