from flask import Blueprint, request, jsonify
from models import db, Vuln, Task
from sqlalchemy.exc import IntegrityError
import uuid

vuln_bp = Blueprint('vuln', __name__, url_prefix='/api/vulns')

@vuln_bp.route('', methods=['GET'])
def get_vulns():
    """获取所有漏洞"""
    try:
        task_id = request.args.get('task_id')
        if task_id:
            vulns = Vuln.query.filter_by(task_id=task_id).all()
        else:
            vulns = Vuln.query.all()
        
        return jsonify({
            'success': True,
            'data': [vuln.to_dict() for vuln in vulns],
            'message': '获取漏洞列表成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取漏洞列表失败: {str(e)}'
        }), 500

@vuln_bp.route('/<vuln_id>', methods=['GET'])
def get_vuln(vuln_id):
    """根据ID获取单个漏洞"""
    try:
        vuln = Vuln.query.get(vuln_id)
        if not vuln:
            return jsonify({
                'success': False,
                'message': '漏洞不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': vuln.to_dict(),
            'message': '获取漏洞成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取漏洞失败: {str(e)}'
        }), 500

@vuln_bp.route('', methods=['POST'])
def create_vuln():
    """创建新漏洞"""
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
        
        vuln = Vuln(
            vuln_type=data.get('vuln_type', ''),
            severity=data.get('severity', 'MEDIUM'),
            description=data.get('description', ''),
            task_id=task_id
        )
        
        # 设置发现时间
        if 'discovered_at' in data:
            from datetime import datetime
            try:
                # 解析ISO格式的时间字符串
                discovered_at_str = data['discovered_at'].replace('Z', '+00:00')
                vuln.discovered_at = datetime.fromisoformat(discovered_at_str)
            except (ValueError, AttributeError):
                # 如果解析失败，使用当前时间
                vuln.discovered_at = datetime.utcnow()
        
        # 设置请求和响应数据
        if 'request' in data:
            vuln.request_dict = data['request']
        if 'response' in data:
            vuln.response_dict = data['response']
        
        db.session.add(vuln)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': vuln.to_dict(),
            'message': '漏洞创建成功'
        }), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '漏洞创建失败：数据完整性错误'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'漏洞创建失败: {str(e)}'
        }), 500

@vuln_bp.route('/<vuln_id>', methods=['PUT'])
def update_vuln(vuln_id):
    """更新漏洞"""
    try:
        vuln = Vuln.query.get(vuln_id)
        if not vuln:
            return jsonify({
                'success': False,
                'message': '漏洞不存在'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        # 更新漏洞字段
        if 'vuln_type' in data:
            vuln.vuln_type = data['vuln_type']
        if 'severity' in data:
            vuln.severity = data['severity']
        if 'description' in data:
            vuln.description = data['description']
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
            vuln.task_id = new_task_id
        if 'request' in data:
            vuln.request_dict = data['request']
        if 'response' in data:
            vuln.response_dict = data['response']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': vuln.to_dict(),
            'message': '漏洞更新成功'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'漏洞更新失败: {str(e)}'
        }), 500

@vuln_bp.route('/<vuln_id>', methods=['DELETE'])
def delete_vuln(vuln_id):
    """删除漏洞"""
    try:
        vuln = Vuln.query.get(vuln_id)
        if not vuln:
            return jsonify({
                'success': False,
                'message': '漏洞不存在'
            }), 404
        
        db.session.delete(vuln)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '漏洞删除成功'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'漏洞删除失败: {str(e)}'
        }), 500

@vuln_bp.route('/task/<task_id>', methods=['GET'])
def get_vulns_by_task(task_id):
    """根据任务ID获取漏洞列表"""
    try:
        # 验证任务是否存在
        task = Task.query.get(task_id)
        if not task:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404
        
        vulns = Vuln.query.filter_by(task_id=task_id).all()
        
        return jsonify({
            'success': True,
            'data': [vuln.to_dict() for vuln in vulns],
            'message': '获取任务漏洞列表成功'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取任务漏洞列表失败: {str(e)}'
        }), 500