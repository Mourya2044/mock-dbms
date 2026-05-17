import sqlite3
import os
from datetime import datetime
import sqlparse

DB_FILE = 'mock_dbms.db'

def _sysdate():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _systimestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

def _nvl(a, b):
    return b if a is None else a

def _nvl2(a, b, c):
    return b if a is not None else c

def _concat(a, b):
    return f"{a or ''}{b or ''}"

def _to_char(val, fmt=None):
    if val is None:
        return None
    val_str = str(val)
    # Basic Oracle date formatting simulation if fmt is provided
    if fmt and isinstance(val, str) and len(val) >= 10:
        try:
            # Try parsing common iso format
            dt = datetime.strptime(val[:19], "%Y-%m-%d %H:%M:%S")
            fmt_py = fmt.upper().replace('YYYY', '%Y').replace('MM', '%m').replace('DD', '%d')
            fmt_py = fmt_py.replace('HH24', '%H').replace('MI', '%M').replace('SS', '%S')
            return dt.strftime(fmt_py)
        except Exception:
            pass
    return val_str

def _to_date(val, fmt=None):
    if val is None:
        return None
    # Returns standard SQLite date string
    val_str = str(val)
    if len(val_str) == 10:
        return val_str + " 00:00:00"
    return val_str

def _to_number(val):
    if val is None:
        return None
    try:
        if '.' in str(val):
            return float(val)
        return int(val)
    except ValueError:
        return None

def _trunc(val, num=0):
    if val is None:
        return None
    try:
        # If it's a number
        fval = float(val)
        factor = 10 ** int(num)
        return int(fval * factor) / factor
    except ValueError:
        # If it's a date string
        val_str = str(val)
        if len(val_str) >= 10:
            return val_str[:10] + " 00:00:00"
        return val

def _mod(a, b):
    if a is None or b is None:
        return None
    try:
        return float(a) % float(b)
    except Exception:
        return None

def _initcap(a):
    return str(a).title() if a is not None else None

def _lpad(a, width, pad=' '):
    if a is None or width is None:
        return None
    try:
        w = int(width)
        s = str(a)
        if len(s) >= w:
            return s[:w]
        p = str(pad) or ' '
        repeats = (w - len(s) + len(p) - 1) // len(p)
        padding = (p * repeats)[:w - len(s)]
        return padding + s
    except Exception:
        return str(a)

def _rpad(a, width, pad=' '):
    if a is None or width is None:
        return None
    try:
        w = int(width)
        s = str(a)
        if len(s) >= w:
            return s[:w]
        p = str(pad) or ' '
        repeats = (w - len(s) + len(p) - 1) // len(p)
        padding = (p * repeats)[:w - len(s)]
        return s + padding
    except Exception:
        return str(a)

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    
    # Register Oracle-compatible functions
    conn.create_function("sysdate", 0, _sysdate)
    conn.create_function("systimestamp", 0, _systimestamp)
    conn.create_function("nvl", 2, _nvl)
    conn.create_function("nvl2", 3, _nvl2)
    conn.create_function("concat", 2, _concat)
    conn.create_function("to_char", 1, _to_char)
    conn.create_function("to_char", 2, _to_char)
    conn.create_function("to_date", 1, _to_date)
    conn.create_function("to_date", 2, _to_date)
    conn.create_function("to_number", 1, _to_number)
    conn.create_function("trunc", 1, _trunc)
    conn.create_function("trunc", 2, _trunc)
    conn.create_function("mod", 2, _mod)
    conn.create_function("initcap", 1, _initcap)
    conn.create_function("lpad", 2, _lpad)
    conn.create_function("lpad", 3, _lpad)
    conn.create_function("rpad", 2, _rpad)
    conn.create_function("rpad", 3, _rpad)
    
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # DUAL table
    cursor.execute("CREATE TABLE IF NOT EXISTS DUAL (DUMMY VARCHAR2(1))")
    cursor.execute("SELECT count(*) FROM DUAL")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO DUAL (DUMMY) VALUES ('X')")

    # DEPT table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS DEPT (
        DEPTNO NUMBER(2) PRIMARY KEY,
        DNAME VARCHAR2(14),
        LOC VARCHAR2(13)
    )
    """)
    cursor.execute("SELECT count(*) FROM DEPT")
    if cursor.fetchone()[0] == 0:
        depts = [
            (10, 'ACCOUNTING', 'NEW YORK'),
            (20, 'RESEARCH', 'DALLAS'),
            (30, 'SALES', 'CHICAGO'),
            (40, 'OPERATIONS', 'BOSTON')
        ]
        cursor.executemany("INSERT INTO DEPT VALUES (?, ?, ?)", depts)

    # EMP table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS EMP (
        EMPNO NUMBER(4) PRIMARY KEY,
        ENAME VARCHAR2(10),
        JOB VARCHAR2(9),
        MGR NUMBER(4),
        HIREDATE DATE,
        SAL NUMBER(7,2),
        COMM NUMBER(7,2),
        DEPTNO NUMBER(2)
    )
    """)
    cursor.execute("SELECT count(*) FROM EMP")
    if cursor.fetchone()[0] == 0:
        emps = [
            (7369, 'SMITH', 'CLERK', 7902, '1980-12-17', 800, None, 20),
            (7499, 'ALLEN', 'SALESMAN', 7698, '1981-02-20', 1600, 300, 30),
            (7521, 'WARD', 'SALESMAN', 7698, '1981-02-22', 1250, 500, 30),
            (7566, 'JONES', 'MANAGER', 7839, '1981-04-02', 2975, None, 20),
            (7654, 'MARTIN', 'SALESMAN', 7698, '1981-09-28', 1250, 1400, 30),
            (7698, 'BLAKE', 'MANAGER', 7839, '1981-05-01', 2850, None, 30),
            (7782, 'CLARK', 'MANAGER', 7839, '1981-06-09', 2450, None, 10),
            (7788, 'SCOTT', 'ANALYST', 7566, '1987-04-19', 3000, None, 20),
            (7839, 'KING', 'PRESIDENT', None, '1981-11-17', 5000, None, 10),
            (7844, 'TURNER', 'SALESMAN', 7698, '1981-09-08', 1500, 0, 30),
            (7876, 'ADAMS', 'CLERK', 7788, '1987-05-23', 1100, None, 20),
            (7900, 'JAMES', 'CLERK', 7698, '1981-12-03', 950, None, 30),
            (7902, 'FORD', 'ANALYST', 7566, '1981-12-03', 3000, None, 20),
            (7934, 'MILLER', 'CLERK', 7782, '1982-01-23', 1300, None, 10)
        ]
        cursor.executemany("INSERT INTO EMP VALUES (?, ?, ?, ?, ?, ?, ?, ?)", emps)

    # SALGRADE table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS SALGRADE (
        GRADE NUMBER,
        LOSAL NUMBER,
        HISAL NUMBER
    )
    """)
    cursor.execute("SELECT count(*) FROM SALGRADE")
    if cursor.fetchone()[0] == 0:
        grades = [
            (1, 700, 1200),
            (2, 1201, 1400),
            (3, 1401, 2000),
            (4, 2001, 3000),
            (5, 3001, 9999)
        ]
        cursor.executemany("INSERT INTO SALGRADE VALUES (?, ?, ?)", grades)

    # BONUS table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS BONUS (
        ENAME VARCHAR2(10),
        JOB VARCHAR2(9),
        SAL NUMBER,
        COMM NUMBER
    )
    """)

    # user_source table for PL/SQL stored procedures/functions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_source (
        name VARCHAR2(100) PRIMARY KEY,
        type VARCHAR2(20),
        text TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def execute_sql(sql_script, params=None):
    """Executes one or more SQL statements and returns the result of the last SELECT statement, or affected rows."""
    conn = get_connection()
    cursor = conn.cursor()
    
    statements = sqlparse.split(sql_script)
    result = {
        'columns': [],
        'rows': [],
        'rows_affected': 0,
        'status': 'success',
        'message': ''
    }
    
    total_affected = 0
    last_select_cols = []
    last_select_rows = []
    
    try:
        for stmt in statements:
            stmt_clean = stmt.strip()
            if not stmt_clean:
                continue
            # Remove trailing semicolon for SQLite execution if present
            if stmt_clean.endswith(';'):
                stmt_clean = stmt_clean[:-1].strip()
                
            if params:
                cursor.execute(stmt_clean, params)
            else:
                cursor.execute(stmt_clean)
                
            if cursor.description:
                last_select_cols = [desc[0] for desc in cursor.description]
                last_select_rows = [list(row) for row in cursor.fetchall()]
            else:
                total_affected += cursor.rowcount if cursor.rowcount > 0 else 0
                
        conn.commit()
        if last_select_cols:
            result['columns'] = last_select_cols
            result['rows'] = last_select_rows
            result['message'] = f"Query executed successfully. {len(last_select_rows)} row(s) fetched."
        else:
            result['rows_affected'] = total_affected
            result['message'] = f"Statement executed successfully. {total_affected} row(s) affected."
            
    except Exception as e:
        conn.rollback()
        result['status'] = 'error'
        result['message'] = str(e)
    finally:
        conn.close()
        
    return result

def get_schema():
    """Returns metadata for all tables in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row['name'] for row in cursor.fetchall()]
    
    schema = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [{'name': r['name'], 'type': r['type'], 'pk': bool(r['pk'])} for r in cursor.fetchall()]
        
        # Fetch 5 sample rows
        try:
            cursor.execute(f"SELECT * FROM {table} LIMIT 5")
            sample_rows = [list(row) for row in cursor.fetchall()]
        except Exception:
            sample_rows = []
            
        schema[table] = {
            'columns': cols,
            'sample_data': sample_rows
        }
        
    conn.close()
    return schema
