from celery_config import create_celery_app
from models import db, Task, Page, Vuln
import time
import random
import requests
from datetime import datetime
import json

# 创建Celery实例
celery = create_celery_app()

@celery.task(bind=True)
def run_ctf_scan_task(self, task_id):
    """异步执行CTF扫描任务"""
    try:
        # 更新任务状态为运行中
        task = Task.query.get(task_id)
        if not task:
            return {'success': False, 'message': '任务不存在'}
        
        task.is_running = True
        db.session.commit()
        
        # 更新任务进度
        self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100, 'status': '开始扫描...'})
        
        # 模拟扫描过程
        target = task.target
        
        # 第一阶段：页面发现
        self.update_state(state='PROGRESS', meta={'current': 20, 'total': 100, 'status': '正在发现页面...'})
        discovered_pages = discover_pages(task_id, target)
        
        # 第二阶段：漏洞扫描
        self.update_state(state='PROGRESS', meta={'current': 60, 'total': 100, 'status': '正在扫描漏洞...'})
        discovered_vulns = scan_vulnerabilities(task_id, target, discovered_pages)
        
        # 第三阶段：Flag搜索
        self.update_state(state='PROGRESS', meta={'current': 80, 'total': 100, 'status': '正在搜索Flag...'})
        flag_found = search_flag(task_id, target, discovered_pages, discovered_vulns)
        
        # 完成任务
        task = Task.query.get(task_id)
        task.is_running = False
        if flag_found:
            task.flag = flag_found
        db.session.commit()
        
        self.update_state(state='SUCCESS', meta={
            'current': 100, 
            'total': 100, 
            'status': '扫描完成',
            'pages_found': len(discovered_pages),
            'vulns_found': len(discovered_vulns),
            'flag_found': bool(flag_found)
        })
        
        return {
            'success': True,
            'message': '扫描任务完成',
            'pages_found': len(discovered_pages),
            'vulns_found': len(discovered_vulns),
            'flag_found': bool(flag_found)
        }
        
    except Exception as e:
        # 发生错误时停止任务
        task = Task.query.get(task_id)
        if task:
            task.is_running = False
            db.session.commit()
        
        self.update_state(state='FAILURE', meta={'error': str(e)})
        return {'success': False, 'message': f'扫描任务失败: {str(e)}'}

def discover_pages(task_id, target):
    """发现页面"""
    pages = []
    
    # 模拟页面发现过程
    common_paths = [
        '/', '/index.html', '/admin', '/login', '/register', 
        '/api', '/config', '/backup', '/test', '/debug'
    ]
    
    for i, path in enumerate(common_paths):
        time.sleep(0.5)  # 模拟网络请求延迟
        
        # 模拟HTTP请求和响应
        url = f"{target.rstrip('/')}{path}"
        
        # 创建模拟的请求和响应数据
        request_data = {
            'method': 'GET',
            'url': url,
            'headers': {
                'User-Agent': 'CTF-Scanner/1.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
        }
        
        response_data = {
            'status_code': random.choice([200, 404, 403, 500]),
            'headers': {
                'Content-Type': 'text/html; charset=utf-8',
                'Server': 'nginx/1.18.0'
            },
            'content': f'<html><head><title>Page {path}</title></head><body>Content for {path}</body></html>'
        }
        
        # 只保存状态码为200的页面
        if response_data['status_code'] == 200:
            page = Page(
                name=f"页面 {path}",
                request=json.dumps(request_data),
                response=json.dumps(response_data),
                description=f"发现的页面: {url}",
                key=path,
                task_id=task_id
            )
            
            db.session.add(page)
            pages.append(page)
    
    db.session.commit()
    return pages

def scan_vulnerabilities(task_id, target, pages):
    """扫描漏洞"""
    vulns = []
    
    # 模拟漏洞扫描
    vuln_types = ['SQL注入', 'XSS', 'CSRF', '文件包含', '命令注入', '目录遍历']
    
    for page in pages:
        if random.random() < 0.3:  # 30%概率发现漏洞
            vuln_type = random.choice(vuln_types)
            severity = random.choice(['HIGH', 'MEDIUM', 'LOW'])
            
            request_data = {
                'method': 'POST',
                'url': f"{target}{page.key}",
                'headers': {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                'data': 'param=test_payload'
            }
            
            response_data = {
                'status_code': 200,
                'headers': {
                    'Content-Type': 'text/html'
                },
                'content': f'Vulnerable response for {vuln_type}'
            }
            
            vuln = Vuln(
                vuln_type=vuln_type,
                severity=severity,
                description=f"在页面 {page.key} 发现 {vuln_type} 漏洞",
                request=json.dumps(request_data),
                response=json.dumps(response_data),
                task_id=task_id
            )
            
            db.session.add(vuln)
            vulns.append(vuln)
            
            time.sleep(0.3)  # 模拟扫描延迟
    
    db.session.commit()
    return vulns

def search_flag(task_id, target, pages, vulns):
    """搜索Flag"""
    time.sleep(1)  # 模拟Flag搜索过程
    
    # 模拟Flag发现逻辑
    if vulns and random.random() < 0.6:  # 如果有漏洞，60%概率找到Flag
        flags = [
            'flag{ctf_scanner_found_this}',
            'CTF{async_task_success}',
            'flag{vulnerability_exploitation}',
            'CTF{page_discovery_complete}'
        ]
        return random.choice(flags)
    
    return None

@celery.task
def stop_ctf_scan_task(task_id):
    """停止CTF扫描任务"""
    try:
        task = Task.query.get(task_id)
        if task:
            task.is_running = False
            db.session.commit()
            return {'success': True, 'message': '任务已停止'}
        return {'success': False, 'message': '任务不存在'}
    except Exception as e:
        return {'success': False, 'message': f'停止任务失败: {str(e)}'}