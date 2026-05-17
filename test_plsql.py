import db
import plsql_interpreter

def run_tests():
    print("\n--- Test 1: Pure SQL DUAL ---")
    res1 = db.execute_sql("SELECT sysdate(), initcap('test') FROM DUAL;")
    print("Columns:", res1['columns'])
    print("Rows:", res1['rows'])
    assert len(res1['rows']) == 1
    
    print("\n--- Test 2: Anonymous Block & DBMS_OUTPUT ---")
    code2 = """
    DECLARE
        v_name VARCHAR2(20) := 'Alice';
        v_num NUMBER := 100;
    BEGIN
        DBMS_OUTPUT.PUT_LINE('Hello ' || v_name);
        DBMS_OUTPUT.PUT_LINE('Number: ' || v_num);
    END;
    """
    res2 = plsql_interpreter.execute_plsql(code2)
    print("Output:", res2['dbms_output'])
    assert len(res2['dbms_output']) == 2
    assert res2['dbms_output'][0] == 'Hello Alice'

    print("\n--- Test 3: Cursor FOR Loop ---")
    code3 = """
    DECLARE
        CURSOR c IS SELECT ename, sal FROM emp WHERE deptno = 10;
    BEGIN
        FOR r IN c LOOP
            DBMS_OUTPUT.PUT_LINE(r.ename || ': ' || r.sal);
        END LOOP;
    END;
    """
    res3 = plsql_interpreter.execute_plsql(code3)
    print("Output:", res3['dbms_output'])
    assert len(res3['dbms_output']) > 0

    print("\n--- Test 4: IF / ELSIF Control Flow ---")
    code4 = """
    DECLARE
        v_val NUMBER := 25;
    BEGIN
        IF v_val > 50 THEN
            DBMS_OUTPUT.PUT_LINE('Greater');
        ELSIF v_val = 25 THEN
            DBMS_OUTPUT.PUT_LINE('Exact');
        ELSE
            DBMS_OUTPUT.PUT_LINE('Lesser');
        END IF;
    END;
    """
    res4 = plsql_interpreter.execute_plsql(code4)
    print("Output:", res4['dbms_output'])
    assert res4['dbms_output'][0] == 'Exact'

    print("\n--- Test 5: Exception Handling ---")
    code5 = """
    DECLARE
        v_ename VARCHAR2(20);
    BEGIN
        SELECT ename INTO v_ename FROM emp WHERE empno = 9999;
        DBMS_OUTPUT.PUT_LINE(v_ename);
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            DBMS_OUTPUT.PUT_LINE('Caught No Data Found');
    END;
    """
    res5 = plsql_interpreter.execute_plsql(code5)
    print("Output:", res5['dbms_output'])
    assert res5['dbms_output'][0] == 'Caught No Data Found'

    print("\n--- Test 6: Create & Call Procedure ---")
    code6_create = """
    CREATE OR REPLACE PROCEDURE greet_emp(p_empno NUMBER) AS
        v_ename VARCHAR2(20);
    BEGIN
        SELECT ename INTO v_ename FROM emp WHERE empno = p_empno;
        DBMS_OUTPUT.PUT_LINE('Greetings ' || v_ename);
    END;
    """
    res6_create = plsql_interpreter.execute_plsql(code6_create)
    print("Create Output:", res6_create['dbms_output'])
    
    code6_call = """
    BEGIN
        CALL greet_emp(7369);
    END;
    """
    res6_call = plsql_interpreter.execute_plsql(code6_call)
    print("Call Output:", res6_call['dbms_output'])
    assert res6_call['dbms_output'][0] == 'Greetings SMITH'

    print("\nALL TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    run_tests()
