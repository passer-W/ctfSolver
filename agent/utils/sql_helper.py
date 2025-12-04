import sqlite3
from config.config import DB_PATH

class SQLiteHelper:
    @staticmethod
    def get_connection():
        """初始化数据库连接"""
        conn = sqlite3.connect(DB_PATH)
        return conn, conn.cursor()

    @staticmethod
    def execute_query(query, params=None):
        """执行查询操作"""
        conn, cursor = SQLiteHelper.get_connection()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            return result
        except sqlite3.Error as e:
            raise e
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def execute_modify(query, params=None):
        """执行增删改操作"""
        conn, cursor = SQLiteHelper.get_connection()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return True
        except sqlite3.Error as e:
            raise e
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def insert_record(table, data):
        """插入记录
        :param table: 表名
        :param data: 字典格式的数据 {'column': value}
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return SQLiteHelper.execute_modify(query, tuple(data.values()))

    @staticmethod
    def update_record(table, data, condition):
        """更新记录
        :param table: 表名
        :param data: 要更新的数据 {'column': value}
        :param condition: 更新条件 {'column': value}
        """
        set_clause = ', '.join([f"{k}=?" for k in data.keys()])
        where_clause = ' AND '.join([f"{k}=?" for k in condition.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        params = tuple(list(data.values()) + list(condition.values()))
        return SQLiteHelper.execute_modify(query, params)

    @staticmethod
    def delete_record(table, condition):
        """删除记录
        :param table: 表名
        :param condition: 删除条件 {'column': value}
        """
        where_clause = ' AND '.join([f"{k}=?" for k in condition.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"
        return SQLiteHelper.execute_modify(query, tuple(condition.values()))

    @staticmethod
    def select_records(table, columns="*", condition=None):
        """查询记录
        :param table: 表名
        :param columns: 要查询的列，默认所有列
        :param condition: 查询条件 {'column': value}
        """
        query = f"SELECT {columns} FROM {table}"
        params = None
        if condition:
            where_clause = ' AND '.join([f"{k}=?" for k in condition.keys()])
            query += f" WHERE {where_clause}"
            params = tuple(condition.values())
        return SQLiteHelper.execute_query(query, params)

    @staticmethod
    def fetch_one(query, params=None):
        """查询单条记录
        :param query: SQL查询语句
        :param params: 查询参数
        """
        result = SQLiteHelper.execute_query(query, params)
        return result[0] if result else None
