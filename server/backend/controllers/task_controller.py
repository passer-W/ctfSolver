from flask import Blueprint, request, jsonify
from models import db, Task, Page, Vuln, Agent
from sqlalchemy.exc import IntegrityError
import uuid

task_bp = Blueprint('task', __name__, url_prefix='/api/tasks')
@task_bp.route('', methods=['GET'])
def get_tasks():
    """获取所有任务（支持分页）"""
    try:
        # 获取查询参数
        agent_id = request.args.get('agent_id')
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # 限制每页数量不超过100
        per_page = min(per_page, 100)

        # 构建查询
        query = Task.query
        if agent_id:
            query = query.filter(Task.agent_id == agent_id)
        if status:
            query = query.filter(Task.status == status)

        # 分页查询
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        tasks = pagination.items

        return jsonify({
            'success': True,
            'data': [task.to_dict() for task in tasks],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            },
            'message': '获取任务列表成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取任务列表失败: {str(e)}'
        }), 500

@task_bp.route('/<task_id>', methods=['GET'])
def get_task(task_id):
    """根据ID获取单个任务"""
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404
        
        # 检查是否需要包含消息
        include_messages = request.args.get('include_messages', 'false').lower() == 'true'
        
        return jsonify({
            'success': True,
            'data': task.to_dict(include_messages=include_messages),
            'message': '获取任务成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取任务失败: {str(e)}'
        }), 500

@task_bp.route('', methods=['POST'])
def create_task():
    """创建新任务"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        # 验证agent_id是否存在（如果提供了的话）
        agent_id = data.get('agent_id')
        if agent_id:
            agent = Agent.query.get(agent_id)
            if not agent:
                return jsonify({
                    'success': False,
                    'message': '指定的Agent不存在'
                }), 400
        
        task = Task(
            target=data.get('target', ''),
            description=data.get('description', ''),
            is_running=data.get('is_running', False),
            flag=data.get('flag', ''),
            task_path=data.get('task_path'),
            agent_id=agent_id
        )
        
        db.session.add(task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': task.to_dict(),
            'message': '任务创建成功'
        }), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '任务创建失败：数据完整性错误'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'任务创建失败: {str(e)}'
        }), 500

@task_bp.route('/<task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务"""
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        # 验证新的agent_id是否存在（如果提供了的话）
        if 'agent_id' in data:
            new_agent_id = data['agent_id']
            if new_agent_id:
                agent = Agent.query.get(new_agent_id)
                if not agent:
                    return jsonify({
                        'success': False,
                        'message': '指定的Agent不存在'
                    }), 400
                    
            task.agent_id = new_agent_id
        
        # 更新任务字段
        if 'target' in data:
            task.target = data['target']
        if 'description' in data:
            task.description = data['description']
        if 'is_running' in data:
            task.is_running = data['is_running']
        if 'flag' in data:
            task.flag = data['flag']
        if 'task_path' in data:
            task.task_path = data['task_path']
        if 'status' in data:
            task.status = data['status']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': task.to_dict(),
            'message': '任务更新成功'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'任务更新失败: {str(e)}'
        }), 500

@task_bp.route('/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404
        
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '任务删除成功'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'任务删除失败: {str(e)}'
        }), 500

@task_bp.route('/<task_id>/toggle-running', methods=['PATCH'])
def toggle_task_running(task_id):
    """切换任务运行状态"""
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404
        
        # 切换运行状态
        task.is_running = not task.is_running
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': task.to_dict(),
            'message': f'任务状态已切换为{"运行中" if task.is_running else "已停止"}'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'切换任务状态失败: {str(e)}'
        }), 500