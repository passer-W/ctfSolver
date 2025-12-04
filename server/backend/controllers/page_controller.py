from flask import Blueprint, request, jsonify
from models import db, Page, Task
from sqlalchemy.exc import IntegrityError
import uuid

page_bp = Blueprint('page', __name__, url_prefix='/api/pages')

@page_bp.route('', methods=['GET'])
def get_pages():
    """获取所有页面"""
    try:
        task_id = request.args.get('task_id')
        if task_id:
            pages = Page.query.filter_by(task_id=task_id).all()
        else:
            pages = Page.query.all()
        
        return jsonify({
            'success': True,
            'data': [page.to_dict() for page in pages],
            'message': '获取页面列表成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取页面列表失败: {str(e)}'
        }), 500

@page_bp.route('/<page_id>', methods=['GET'])
def get_page(page_id):
    """根据ID获取单个页面"""
    try:
        page = Page.query.get(page_id)
        if not page:
            return jsonify({
                'success': False,
                'message': '页面不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': page.to_dict(),
            'message': '获取页面成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取页面失败: {str(e)}'
        }), 500

@page_bp.route('', methods=['POST'])
def create_page():
    """创建新页面"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        # 验证任务是否存在
        task_id = data.get('task_id')
        if task_id:
            task = Task.query.get(task_id)
            if not task:
                return jsonify({
                    'success': False,
                    'message': '关联的任务不存在'
                }), 400
        
        page = Page(
            name=data.get('name', ''),
            description=data.get('description', ''),
            key=data.get('key', ''),
            task_id=task_id
        )
        
        # 设置发现时间
        if 'discovered_at' in data:
            from datetime import datetime
            try:
                # 解析ISO格式的时间字符串
                discovered_at_str = data['discovered_at'].replace('Z', '+00:00')
                page.discovered_at = datetime.fromisoformat(discovered_at_str)
            except (ValueError, AttributeError):
                # 如果解析失败，使用当前时间
                page.discovered_at = datetime.utcnow()
        
        # 设置请求和响应数据
        if 'request' in data:
            page.request_dict = data['request']
        if 'response' in data:
            page.response_dict = data['response']
        
        db.session.add(page)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': page.to_dict(),
            'message': '页面创建成功'
        }), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '页面创建失败：数据完整性错误'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'页面创建失败: {str(e)}'
        }), 500

@page_bp.route('/<page_id>', methods=['PUT'])
def update_page(page_id):
    """更新页面"""
    try:
        page = Page.query.get(page_id)
        if not page:
            return jsonify({
                'success': False,
                'message': '页面不存在'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        # 更新页面字段
        if 'name' in data:
            page.name = data['name']
        if 'description' in data:
            page.description = data['description']
        if 'key' in data:
            page.key = data['key']
        if 'task_id' in data:
            # 验证新的任务是否存在
            new_task_id = data['task_id']
            if new_task_id:
                task = Task.query.get(new_task_id)
                if not task:
                    return jsonify({
                        'success': False,
                        'message': '关联的任务不存在'
                    }), 400
            page.task_id = new_task_id
        if 'request' in data:
            page.request_dict = data['request']
        if 'response' in data:
            page.response_dict = data['response']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': page.to_dict(),
            'message': '页面更新成功'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'页面更新失败: {str(e)}'
        }), 500

@page_bp.route('/<page_id>', methods=['DELETE'])
def delete_page(page_id):
    """删除页面"""
    try:
        page = Page.query.get(page_id)
        if not page:
            return jsonify({
                'success': False,
                'message': '页面不存在'
            }), 404
        
        db.session.delete(page)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '页面删除成功'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'页面删除失败: {str(e)}'
        }), 500

@page_bp.route('/task/<task_id>', methods=['GET'])
def get_pages_by_task(task_id):
    """根据任务ID获取页面列表"""
    try:
        # 验证任务是否存在
        task = Task.query.get(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404
        
        pages = Page.query.filter_by(task_id=task_id).all()
        
        return jsonify({
            'success': True,
            'data': [page.to_dict() for page in pages],
            'message': '获取任务页面列表成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取任务页面列表失败: {str(e)}'
        }), 500