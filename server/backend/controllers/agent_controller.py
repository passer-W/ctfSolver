from flask import Blueprint, request, jsonify
from models import db, Agent
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import uuid

agent_bp = Blueprint('agent', __name__, url_prefix='/api/agents')

@agent_bp.route('', methods=['GET'])
def get_agents():
    """获取所有Agent"""
    try:
        agents = Agent.query.all()
        return jsonify({
            'success': True,
            'data': [agent.to_dict() for agent in agents],
            'message': '获取Agent列表成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取Agent列表失败: {str(e)}'
        }), 500

@agent_bp.route('/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    """根据ID获取单个Agent"""
    try:
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({
                'success': False,
                'message': 'Agent不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': agent.to_dict(),
            'message': '获取Agent成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取Agent失败: {str(e)}'
        }), 500

@agent_bp.route('/register', methods=['POST'])
def register_agent():
    """注册新Agent"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        # 验证必需字段
        required_fields = ['name', 'host', 'port']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必需字段: {field}'
                }), 400
        
        current_time = datetime.utcnow()
        
        # 创建新Agent
        agent = Agent(
            name=data['name'],
            host=data['host'],
            port=data['port'],
            status=data.get('status', 'online'),
            last_heartbeat=current_time,
            last_seen=current_time
        )
        
        # 设置启动时间
        if 'start_time' in data:
            agent.start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        else:
            agent.start_time = current_time
        
        # 设置能力和元数据
        if 'capabilities' in data:
            agent.capabilities_dict = data['capabilities']
        if 'metadata' in data:
            agent.metadata_dict = data['metadata']
        
        db.session.add(agent)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': agent.to_dict(),
            'message': 'Agent注册成功'
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Agent注册失败：数据完整性错误'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Agent注册失败: {str(e)}'
        }), 500

@agent_bp.route('/<agent_id>/heartbeat', methods=['POST'])
def agent_heartbeat(agent_id):
    """Agent心跳更新"""
    try:
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({
                'success': False,
                'message': 'Agent不存在'
            }), 404
        
        data = request.get_json() or {}
        current_time = datetime.utcnow()
        
        # 更新心跳时间和状态
        agent.last_heartbeat = current_time
        agent.last_seen = current_time
        agent.status = data.get('status', 'online')
        
        # 更新元数据（如果提供）
        if 'metadata' in data:
            agent.metadata_dict = data['metadata']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': agent.to_dict(),
            'message': '心跳更新成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'心跳更新失败: {str(e)}'
        }), 500

@agent_bp.route('/<agent_id>', methods=['PUT'])
def update_agent(agent_id):
    """更新Agent信息"""
    try:
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({
                'success': False,
                'message': 'Agent不存在'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        # 更新Agent字段
        if 'name' in data:
            agent.name = data['name']
        if 'host' in data:
            agent.host = data['host']
        if 'port' in data:
            agent.port = data['port']
        if 'status' in data:
            agent.status = data['status']
        if 'capabilities' in data:
            agent.capabilities_dict = data['capabilities']
        if 'metadata' in data:
            agent.metadata_dict = data['metadata']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': agent.to_dict(),
            'message': 'Agent更新成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Agent更新失败: {str(e)}'
        }), 500

@agent_bp.route('/<agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    """删除Agent"""
    try:
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({
                'success': False,
                'message': 'Agent不存在'
            }), 404
        
        db.session.delete(agent)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Agent删除成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Agent删除失败: {str(e)}'
        }), 500

@agent_bp.route('/status', methods=['GET'])
def get_agents_status():
    """获取所有Agent状态概览"""
    try:
        agents = Agent.query.all()
        
        # 统计信息
        total_agents = len(agents)
        online_agents = len([a for a in agents if a.status == 'online'])
        offline_agents = len([a for a in agents if a.status == 'offline'])
        
        # 检查超时的Agent（5分钟没有心跳）
        timeout_threshold = datetime.utcnow() - timedelta(minutes=5)
        for agent in agents:
            if agent.last_heartbeat and agent.last_heartbeat < timeout_threshold:
                if agent.status != 'offline':
                    agent.status = 'offline'
                    db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'agents': [agent.to_dict() for agent in agents],
                'statistics': {
                    'total_agents': total_agents,
                    'online_agents': online_agents,
                    'offline_agents': offline_agents
                }
            },
            'message': '获取Agent状态成功'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取Agent状态失败: {str(e)}'
        }), 500