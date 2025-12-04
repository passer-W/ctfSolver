from flask import Blueprint, request, jsonify
from models import db, Process, History
from sqlalchemy.exc import IntegrityError
import uuid
process_bp = Blueprint('process', __name__, url_prefix='/api/process')


@process_bp.route('/<process_id>', methods=['POST'])
def create_process(process_id):
    """创建一个新的process，使用路径中的process_id"""
    try:
        data = request.get_json() or {}
        # 可选字段
        addition = data.get('addition', None)
        # 默认状态为 run
        status = 'run'

        process = Process(id=process_id, status=status, addition=addition)
        db.session.add(process)
        db.session.commit()

        return jsonify({'success': True, 'data': process.to_dict(), 'message': 'process创建成功'}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'process创建失败：数据完整性错误'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'process创建失败: {str(e)}'}), 500


@process_bp.route('/<process_id>', methods=['GET'])
def get_process_messages(process_id):
    """获取指定process的所有message（History）"""
    try:
        process = Process.query.get(process_id)
        if not process:
            return jsonify({'success': True, 'data': []}), 200

        # 查询所有与该process相关的历史记录
        process_histories = [h.to_dict() for h in process.histories]
        
        return jsonify({
            'success': True,
            'data': process_histories,
            'message': '获取消息列表成功'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取消息列表失败: {str(e)}'}), 500

@process_bp.route('/<process_id>/message', methods=['POST'])
def add_process_message(process_id):
    """为指定process新增一条message（History）"""
    try:
        process = Process.query.get(process_id)
        data = request.get_json() or {}
        metadata = data.get('metadata', {})

        # 创建新的历史记录，直接将传入的metadata赋值
        history = History()
        history.process = process
        history.metadata_dict = metadata
        
        db.session.add(history)
        db.session.commit()

        return jsonify({'success': True, 'data': history.to_dict(), 'message': '消息创建成功'}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'success': False, 'message': '消息创建失败：数据完整性错误'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'消息创建失败: {str(e)}'}), 500

@process_bp.route('/<process_id>/status', methods=['GET'])
def get_process_status(process_id):
    """获取指定process的状态"""
    try:
        process = Process.query.get(process_id)
        if not process:
            return jsonify({'success': True, 'message': '未找到对应的process'}), 404

        return jsonify({'success': True, 'data': {'status': process.status}, 'message': '获取状态成功'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取状态失败: {str(e)}'}), 500

@process_bp.route('/<process_id>/status', methods=['POST'])
def update_process_status(process_id):
    """修改指定process的状态（run/pause）"""
    try:
        process = Process.query.get(process_id)
        if not process:
            return jsonify({'success': False, 'message': '未找到对应的process'}), 404

        data = request.get_json() or {}
        new_status = data.get('status')
        if new_status not in {'run', 'pause'}:
            return jsonify({'success': False, 'message': '状态非法，仅支持 run/pause'}), 400

        # 可选更新 addition
        addition = data.get('addition', None)
        if addition is not None:
            process.addition = addition

        process.status = new_status
        db.session.commit()

        return jsonify({'success': True, 'data': {'status': process.status, 'addition': process.addition}, 'message': '状态更新成功'}), 200
    except IntegrityError:
        db.session.rollback()
        return jsonify({'success': False, 'message': '状态更新失败：数据完整性错误'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'状态更新失败: {str(e)}'}), 500