# Mock DBMS - SQL & PL/SQL Practice Playground

A standalone, feature-rich Mock DBMS Web Application designed for students, developers, and professionals to practice SQL and PL/SQL queries. 

Since standard lightweight databases like SQLite do not support PL/SQL (Oracle's procedural extension), this application implements a custom PL/SQL interpreter in Python backed by an SQLite engine enriched with Oracle-compatible built-in functions and classic sample datasets (`EMP`, `DEPT`, `DUAL`).

## Features

- **Stunning Minimalist UI**: Clean, high-contrast dark mode interface focusing on crisp typography and optimal workflow.
- **Classic Practice Datasets**: Pre-loaded with Oracle's standard `EMP`, `DEPT`, `SALGRADE`, `BONUS`, and `DUAL` tables.
- **AI Assistant Integration (Gemini 2.5 Flash)**: Features an "Ask AI" input bar directly above the SQL editor. Ask it to generate table definitions or insert mock data in plain English, and it will automatically generate and execute the SQL.
- **Oracle Compatibility Layer**: Emulates Oracle SQL built-in functions including `sysdate`, `systimestamp`, `nvl`, `nvl2`, `concat`, `to_char`, `to_date`, `to_number`, `trunc`, `mod`, `initcap`, `lpad`, `rpad`.
- **Custom PL/SQL Engine**: Supports core procedural constructs:
  - Anonymous blocks (`DECLARE ... BEGIN ... EXCEPTION ... END;`)
  - Variables (`VARCHAR2`, `NUMBER`, `DATE`, `BOOLEAN`, `%TYPE`, `%ROWTYPE`)
  - Control Flow (`IF/ELSIF/ELSE`, `CASE`)
  - Loops (`WHILE`, `FOR`, `LOOP..EXIT WHEN`, Cursor `FOR` loops)
  - Cursors (`OPEN`, `FETCH INTO`, `CLOSE`, attributes `%FOUND`, `%NOTFOUND`, `%ROWCOUNT`, `%ISOPEN`)
  - Embedded SQL & DML (`SELECT INTO`, `INSERT`, `UPDATE`, `DELETE`)
  - Exception Handling (`NO_DATA_FOUND`, `TOO_MANY_ROWS`, `ZERO_DIVIDE`, `OTHERS`, user-defined)
  - Stored Procedures & Functions (`CREATE OR REPLACE PROCEDURE / FUNCTION`)
  - Console Output (`DBMS_OUTPUT.PUT_LINE`)

## Installation & Running

### 1. Prerequisites
- Python 3.9+ installed.
- A Google Gemini API key (available via [Google AI Studio](https://aistudio.google.com/app/apikey)).

### 2. Environment Setup
Clone or open the project folder, then set up your environment variables:
1. Rename the `.env.example` file to `.env`.
2. Open `.env` and add your Gemini API key:
   ```env
   GEMINI_API_KEY=AIzaSy...your_api_key_here...
   ```

### 3. Install Dependencies
Install the required packages (including `aiohttp`, `google-genai`, and `python-dotenv`):
```bash
pip install -r requirements.txt
```

### 4. Start the Server
Run the asynchronous web application:
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:8080`.

## Quick Practice Examples

### 1. AI Assistant Prompt
Type the following into the **Ask AI** bar above the editor:
> *"Create a table for library books with 5 rows of mock data"*

The AI will automatically generate and execute the DDL and DML statements, updating your Schema Explorer instantly!

### 2. Pure SQL
```sql
SELECT empno, ename, job, sal, deptno 
FROM emp 
WHERE sal > 2000 
ORDER BY sal DESC;
```

### 3. Cursor FOR Loop (PL/SQL)
```sql
DECLARE
    CURSOR c_emp IS SELECT ename, sal FROM emp WHERE deptno = 30;
BEGIN
    DBMS_OUTPUT.PUT_LINE('--- Dept 30 Employees ---');
    FOR r IN c_emp LOOP
        DBMS_OUTPUT.PUT_LINE(r.ename || ' earns $' || r.sal);
    END LOOP;
END;
```

### 4. Stored Procedure Creation
```sql
CREATE OR REPLACE PROCEDURE award_bonus(p_empno NUMBER, p_bonus NUMBER) AS
    v_ename VARCHAR2(20);
    v_sal NUMBER;
BEGIN
    SELECT ename, sal INTO v_ename, v_sal FROM emp WHERE empno = p_empno;
    INSERT INTO bonus (ename, job, sal, comm) VALUES (v_ename, 'AWARDED', v_sal, p_bonus);
    DBMS_OUTPUT.PUT_LINE('Successfully awarded $' || p_bonus || ' to ' || v_ename);
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        DBMS_OUTPUT.PUT_LINE('Cannot award bonus: Employee not found.');
END;
```
