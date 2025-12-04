CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
CREATE TABLE IF NOT EXISTS solutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            solution TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page TEXT,
            action TEXT,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            parent_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );


CREATE TABLE IF NOT EXISTS pages (
            id TEXT PRIMARY KEY,
            parent_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );


CREATE TABLE IF NOT EXISTS vulns (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            vuln_type TEXT,
            desc TEXT,
            request_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)