# Mock DBMS - SQL & PL/SQL Practice Playground

A standalone, feature-rich Mock DBMS Web Application designed for students, developers, and professionals to practice SQL and PL/SQL queries. 

Since standard lightweight databases like SQLite do not support PL/SQL (Oracle's procedural extension), this application implements a custom PL/SQL interpreter in Python backed by an SQLite engine enriched with Oracle-compatible built-in functions and classic sample datasets (`EMP`, `DEPT`, `DUAL`).

## Features

- **Stunning Minimalist UI**: Clean, high-contrast dark mode interface focusing on crisp typography and optimal workflow.
- **Classic Practice Datasets**: Pre-loaded with Oracle's standard `EMP`, `DEPT`, `SALGRADE`, `BONUS`, and `DUAL` tables.
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

1. Ensure Python 3.9+ is installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```
4. Open your browser and navigate to `http://127.0.0.1:8080`.

## Quick Practice Examples

### 1. Pure SQL
```sql
SELECT empno, ename, job, sal, deptno 
FROM emp 
WHERE sal > 2000 
ORDER BY sal DESC;
```

### 2. Cursor FOR Loop (PL/SQL)
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

### 3. Stored Procedure Creation
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
