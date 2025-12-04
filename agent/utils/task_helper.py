import json

from utils import sql_helper


def get_all_vulns(task_id):
    sql = f"SELECT * FROM vulns WHERE task_id = '{task_id}'"
    results = sql_helper.SQLiteHelper.execute_query(sql)
    vulns = []
    for result in results:
        vulns.append({
            'id': result[0],
            'task_id': result[1],
            'vuln_type': result[2],
            'desc': result[3],
            'request_json': json.loads(result[4]),
        })
    return vulns
