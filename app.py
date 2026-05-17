import os
import time
from aiohttp import web
import db
import plsql_interpreter
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

async def handle_ai(request):
    try:
        data = await request.json()
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return web.json_response({'status': 'error', 'message': 'No prompt provided.'}, status=400)
            
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key or api_key == 'your_api_key_here':
            return web.json_response({'status': 'error', 'message': 'GEMINI_API_KEY is not configured in .env'}, status=400)
            
        # Initialize client
        client = genai.Client(api_key=api_key)
        
        # Fetch current database schema to provide context to AI
        current_schema = db.get_schema()
        schema_context = "Current Database Schema:\n"
        for table_name, table_info in current_schema.items():
            cols = ", ".join([f"{c['name']} ({c['type']})" for c in table_info['columns']])
            schema_context += f"- Table: {table_name} | Columns: {cols}\n"
            if table_info['sample_data']:
                sample_strs = [str(row) for row in table_info['sample_data'][:2]] # show up to 2 sample rows
                schema_context += f"  Sample rows: {sample_strs}\n"
        
        system_msg = (
            "You are an expert AI assistant for an Oracle SQL practice playground.\n"
            f"{schema_context}\n"
            "The user will ask you to create tables, insert mock data, or perform queries/actions on existing tables.\n"
            "Output ONLY valid SQL statements (DDL/DML/Queries) separated by semicolons. Do not include markdown formatting, explanations, or any other text."
        )
        
        # Generate content asynchronously
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_msg,
                temperature=0.2,
            )
        )
        sql = response.text.strip()
        
        # Remove markdown blocks if the model still outputs them
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
            
        return web.json_response({'status': 'success', 'sql': sql.strip()})
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def handle_schema(request):
    try:
        schema = db.get_schema()
        return web.json_response({'status': 'success', 'schema': schema})
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def handle_execute(request):
    try:
        data = await request.json()
        code = data.get('code', '').strip()
        mode = data.get('mode', 'auto').lower()
        
        if not code:
            return web.json_response({'status': 'error', 'message': 'No code provided.'}, status=400)
            
        start_time = time.time()
        
        # Determine execution mode
        is_plsql = False
        if mode == 'plsql':
            is_plsql = True
        elif mode == 'auto':
            # Auto-detect PL/SQL constructs
            code_upper = code.upper()
            if any(keyword in code_upper for keyword in ('DECLARE', 'BEGIN', 'CREATE PROCEDURE', 'CREATE OR REPLACE PROCEDURE', 'CREATE FUNCTION', 'CREATE OR REPLACE FUNCTION')):
                is_plsql = True
                
        # Execute
        if is_plsql:
            res = plsql_interpreter.execute_plsql(code)
            exec_time = time.time() - start_time
            return web.json_response({
                'status': res.get('status', 'success'),
                'type': 'plsql',
                'dbms_output': res.get('dbms_output', []),
                'message': res.get('message', ''),
                'execution_time_ms': round(exec_time * 1000, 2)
            })
        else:
            res = db.execute_sql(code)
            exec_time = time.time() - start_time
            return web.json_response({
                'status': res.get('status', 'success'),
                'type': 'sql',
                'columns': res.get('columns', []),
                'rows': res.get('rows', []),
                'rows_affected': res.get('rows_affected', 0),
                'message': res.get('message', ''),
                'execution_time_ms': round(exec_time * 1000, 2)
            })
            
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def handle_snippets(request):
    snippets = [
        {
            'title': '1. Simple SQL Query',
            'category': 'SQL',
            'code': 'SELECT empno, ename, job, sal\nFROM emp\nWHERE sal > 2000\nORDER BY sal DESC;'
        },
        {
            'title': '2. DUAL Table & Built-ins',
            'category': 'SQL',
            'code': "SELECT sysdate(), initcap('hello oracle'), nvl(comm, 0)\nFROM emp\nLIMIT 5;"
        },
        {
            'title': '3. Anonymous Block (DBMS_OUTPUT)',
            'category': 'PL/SQL',
            'code': "DECLARE\n    v_name VARCHAR2(50) := 'Oracle Student';\n    v_score NUMBER := 95;\nBEGIN\n    DBMS_OUTPUT.PUT_LINE('Welcome ' || v_name);\n    DBMS_OUTPUT.PUT_LINE('Your practice score is: ' || v_score);\nEND;"
        },
        {
            'title': '4. Cursor FOR Loop',
            'category': 'PL/SQL',
            'code': "DECLARE\n    CURSOR c_emp IS SELECT ename, sal FROM emp WHERE deptno = 30;\nBEGIN\n    DBMS_OUTPUT.PUT_LINE('--- Dept 30 Employees ---');\n    FOR r IN c_emp LOOP\n        DBMS_OUTPUT.PUT_LINE(r.ename || ' earns $' || r.sal);\n    END LOOP;\nEND;"
        },
        {
            'title': '5. IF / ELSIF Control Flow',
            'category': 'PL/SQL',
            'code': "DECLARE\n    v_sal NUMBER := 3500;\nBEGIN\n    IF v_sal > 4000 THEN\n        DBMS_OUTPUT.PUT_LINE('High Salary');\n    ELSIF v_sal BETWEEN 2000 AND 4000 THEN\n        DBMS_OUTPUT.PUT_LINE('Medium Salary');\n    ELSE\n        DBMS_OUTPUT.PUT_LINE('Low Salary');\n    END IF;\nEND;"
        },
        {
            'title': '6. Exception Handling',
            'category': 'PL/SQL',
            'code': "DECLARE\n    v_ename VARCHAR2(20);\nBEGIN\n    -- Expecting ORA-01403 No Data Found\n    SELECT ename INTO v_ename FROM emp WHERE empno = 9999;\n    DBMS_OUTPUT.PUT_LINE('Found: ' || v_ename);\nEXCEPTION\n    WHEN NO_DATA_FOUND THEN\n        DBMS_OUTPUT.PUT_LINE('Error: Employee 9999 does not exist!');\n    WHEN OTHERS THEN\n        DBMS_OUTPUT.PUT_LINE('Unexpected error occurred.');\nEND;"
        },
        {
            'title': '7. Create Stored Procedure',
            'category': 'PL/SQL',
            'code': "CREATE OR REPLACE PROCEDURE award_bonus(p_empno NUMBER, p_bonus NUMBER) AS\n    v_ename VARCHAR2(20);\n    v_sal NUMBER;\nBEGIN\n    SELECT ename, sal INTO v_ename, v_sal FROM emp WHERE empno = p_empno;\n    INSERT INTO bonus (ename, job, sal, comm) VALUES (v_ename, 'AWARDED', v_sal, p_bonus);\n    DBMS_OUTPUT.PUT_LINE('Successfully awarded $' || p_bonus || ' to ' || v_ename);\nEXCEPTION\n    WHEN NO_DATA_FOUND THEN\n        DBMS_OUTPUT.PUT_LINE('Cannot award bonus: Employee not found.');\nEND;"
        },
        {
            'title': '8. Call Stored Procedure',
            'category': 'PL/SQL',
            'code': "BEGIN\n    CALL award_bonus(7369, 500);\nEND;"
        }
    ]
    return web.json_response({'status': 'success', 'snippets': snippets})

async def index_handler(request):
    return web.FileResponse('./static/index.html')

def create_app():
    app = web.Application()
    
    # API Routes
    app.router.add_get('/api/schema', handle_schema)
    app.router.add_post('/api/execute', handle_execute)
    app.router.add_get('/api/snippets', handle_snippets)
    app.router.add_post('/api/ai', handle_ai)
    
    # Static Files & Index
    app.router.add_get('/', index_handler)
    app.router.add_static('/static', './static')
    
    return app

if __name__ == '__main__':
    app = create_app()
    web.run_app(app, host='127.0.0.1', port=8080)
