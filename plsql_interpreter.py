import re
import sqlite3
import db

# --- LEXER ---

KEYWORDS = {
    'DECLARE', 'BEGIN', 'END', 'EXCEPTION', 'IF', 'THEN', 'ELSIF', 'ELSE',
    'CASE', 'WHEN', 'WHILE', 'LOOP', 'FOR', 'IN', 'REVERSE', 'EXIT',
    'OPEN', 'CLOSE', 'FETCH', 'INTO', 'CURSOR', 'IS', 'SELECT', 'INSERT',
    'UPDATE', 'DELETE', 'COMMIT', 'ROLLBACK', 'DBMS_OUTPUT.PUT_LINE',
    'CREATE', 'OR', 'REPLACE', 'PROCEDURE', 'FUNCTION', 'AS', 'RETURN',
    'NUMBER', 'VARCHAR2', 'VARCHAR', 'BOOLEAN', 'DATE', 'PRAGMA', 'RAISE',
    'OTHERS', 'NO_DATA_FOUND', 'TOO_MANY_ROWS', 'ZERO_DIVIDE', 'TRUE', 'FALSE',
    'NULL', 'AND', 'OR', 'NOT', 'LIKE', 'BETWEEN', 'MOD', 'CALL'
}

class Token:
    def __init__(self, type_, value, line):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)})"

def tokenize(code):
    # Remove single line comments --...
    code = re.sub(r'--.*', '', code)
    # Remove multi-line comments /*...*/
    code = re.sub(r'/\*[\s\S]*?\*/', '', code)
    
    token_specification = [
        ('DBMS_OUTPUT', r'DBMS_OUTPUT\.PUT_LINE\b'),
        ('NUMBER_LIT',  r'\d+(\.\d+)?'),
        ('STRING_LIT',  r"'[^']*'"),
        ('ASSIGN',      r':='),
        ('DOTDOT',      r'\.\.'),
        ('GE',          r'>='),
        ('LE',          r'<='),
        ('NE',          r'!=|<>'),
        ('CONCAT',      r'\|\|'),
        ('GT',          r'>'),
        ('LT',          r'<'),
        ('EQ',          r'='),
        ('SEMI',        r';'),
        ('COMMA',       r','),
        ('LPAREN',      r'\('),
        ('RPAREN',      r'\)'),
        ('DOT',         r'\.'),
        ('PERCENT',     r'%'),
        ('PLUS',        r'\+'),
        ('MINUS',       r'-'),
        ('STAR',        r'\*'),
        ('SLASH',       r'/'),
        ('ID',          r'[A-Za-z_][A-Za-z0-9_]*'),
        ('NEWLINE',     r'\n'),
        ('SKIP',        r'[ \t\r]+'),
        ('MISMATCH',    r'.'),
    ]
    
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
    line_num = 1
    tokens = []
    
    for mo in re.finditer(tok_regex, code, re.IGNORECASE):
        kind = mo.lastgroup
        value = mo.group()
        if kind == 'NEWLINE':
            line_num += 1
            continue
        elif kind == 'SKIP':
            continue
        elif kind == 'MISMATCH':
            raise RuntimeError(f"Lexer error on line {line_num}: Unexpected character {value}")
        elif kind == 'ID':
            val_upper = value.upper()
            if val_upper in KEYWORDS:
                kind = val_upper
            tokens.append(Token(kind, value, line_num))
        elif kind == 'DBMS_OUTPUT':
            tokens.append(Token('DBMS_OUTPUT', value, line_num))
        else:
            tokens.append(Token(kind, value, line_num))
            
    tokens.append(Token('EOF', 'EOF', line_num))
    return tokens


# --- AST NODES ---

class AST: pass
class Program(AST):
    def __init__(self, statements): self.statements = statements
class Block(AST):
    def __init__(self, decls, body, exceptions):
        self.decls = decls
        self.body = body
        self.exceptions = exceptions
class VarDecl(AST):
    def __init__(self, name, datatype, init_expr):
        self.name = name
        self.datatype = datatype
        self.init_expr = init_expr
class CursorDecl(AST):
    def __init__(self, name, select_sql):
        self.name = name
        self.select_sql = select_sql
class Assign(AST):
    def __init__(self, target, expr):
        self.target = target
        self.expr = expr
class IfStmt(AST):
    def __init__(self, branches, else_body):
        self.branches = branches
        self.else_body = else_body
class CaseStmt(AST):
    def __init__(self, case_expr, branches, else_body):
        self.case_expr = case_expr
        self.branches = branches
        self.else_body = else_body
class WhileLoop(AST):
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body
class BasicLoop(AST):
    def __init__(self, body):
        self.body = body
class ExitStmt(AST):
    def __init__(self, when_cond):
        self.when_cond = when_cond
class ForLoop(AST):
    def __init__(self, loop_var, start_expr, end_expr, reverse, body):
        self.loop_var = loop_var
        self.start_expr = start_expr
        self.end_expr = end_expr
        self.reverse = reverse
        self.body = body
class CursorForLoop(AST):
    def __init__(self, loop_var, cursor_name, body):
        self.loop_var = loop_var
        self.cursor_name = cursor_name
        self.body = body
class OpenStmt(AST):
    def __init__(self, cursor_name): self.cursor_name = cursor_name
class FetchStmt(AST):
    def __init__(self, cursor_name, target_vars):
        self.cursor_name = cursor_name
        self.target_vars = target_vars
class CloseStmt(AST):
    def __init__(self, cursor_name): self.cursor_name = cursor_name
class SelectIntoStmt(AST):
    def __init__(self, select_sql, target_vars, into_clause_str):
        self.select_sql = select_sql
        self.target_vars = target_vars
        self.into_clause_str = into_clause_str
class DmlStmt(AST):
    def __init__(self, sql): self.sql = sql
class DbmsOutputStmt(AST):
    def __init__(self, expr): self.expr = expr
class ProcCallStmt(AST):
    def __init__(self, name, args):
        self.name = name
        self.args = args
class CreateProcStmt(AST):
    def __init__(self, name, params, body, is_function, return_type, raw_text):
        self.name = name
        self.params = params
        self.body = body
        self.is_function = is_function
        self.return_type = return_type
        self.raw_text = raw_text
class RaiseStmt(AST):
    def __init__(self, exc_name): self.exc_name = exc_name

class BinaryOp(AST):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right
class UnaryOp(AST):
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr
class Literal(AST):
    def __init__(self, value): self.value = value
class Variable(AST):
    def __init__(self, name): self.name = name
class CursorAttr(AST):
    def __init__(self, cursor_name, attr):
        self.cursor_name = cursor_name
        self.attr = attr
class FuncCall(AST):
    def __init__(self, name, args):
        self.name = name
        self.args = args


# --- PARSER ---

class Parser:
    def __init__(self, tokens, raw_code=""):
        self.tokens = tokens
        self.pos = 0
        self.raw_code = raw_code

    def current(self):
        return self.tokens[self.pos]

    def peek(self, offset=1):
        if self.pos + offset < len(self.tokens):
            return self.tokens[self.pos + offset]
        return self.tokens[-1]

    def consume(self, expected_type=None):
        curr = self.current()
        if expected_type and curr.type != expected_type:
            raise RuntimeError(f"Parser error on line {curr.line}: Expected {expected_type}, got {curr.type} ('{curr.value}')")
        self.pos += 1
        return curr

    def match(self, *types):
        if self.current().type in types:
            return self.consume()
        return None

    def parse(self):
        statements = []
        while self.current().type != 'EOF':
            stmt = self.parse_top_level()
            if stmt:
                statements.append(stmt)
            else:
                if self.current().type != 'EOF':
                    self.consume()
        return Program(statements)

    def parse_top_level(self):
        curr = self.current()
        if curr.type == 'CREATE':
            return self.parse_create_stmt()
        elif curr.type in ('DECLARE', 'BEGIN'):
            return self.parse_block()
        elif curr.type in ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'COMMIT', 'ROLLBACK'):
            # Standalone SQL/DML
            return self.parse_dml_stmt()
        elif curr.type == 'DBMS_OUTPUT':
            return self.parse_dbms_output()
        elif curr.type == 'CALL':
            self.consume()
            name = self.consume('ID').value
            args = []
            if self.match('LPAREN'):
                if self.current().type != 'RPAREN':
                    args.append(self.parse_expr())
                    while self.match('COMMA'):
                        args.append(self.parse_expr())
                self.consume('RPAREN')
            self.match('SEMI')
            return ProcCallStmt(name, args)
        else:
            # Might be a procedure call without CALL keyword
            if curr.type == 'ID':
                name = self.consume('ID').value
                args = []
                if self.match('LPAREN'):
                    if self.current().type != 'RPAREN':
                        args.append(self.parse_expr())
                        while self.match('COMMA'):
                            args.append(self.parse_expr())
                    self.consume('RPAREN')
                self.match('SEMI')
                return ProcCallStmt(name, args)
            self.consume()
            return None

    def parse_create_stmt(self):
        self.consume('CREATE')
        if self.match('OR'):
            self.consume('REPLACE')
            
        is_func = False
        if self.match('FUNCTION'):
            is_func = True
        else:
            self.consume('PROCEDURE')
            
        name = self.consume('ID').value
        params = []
        if self.match('LPAREN'):
            if self.current().type != 'RPAREN':
                params.append(self.parse_param())
                while self.match('COMMA'):
                    params.append(self.parse_param())
            self.consume('RPAREN')
            
        return_type = None
        if is_func:
            self.consume('RETURN')
            return_type = self.parse_datatype()
            
        if not (self.match('AS') or self.match('IS')):
            raise RuntimeError(f"Expected AS or IS in CREATE statement on line {self.current().line}")
            
        # Parse block body
        body = self.parse_block(is_create=True)
        return CreateProcStmt(name, params, body, is_func, return_type, self.raw_code)

    def parse_param(self):
        param_name = self.consume('ID').value
        if self.match('IN'): pass
        if self.match('OUT'): pass
        datatype = self.parse_datatype()
        return (param_name, datatype)

    def parse_datatype(self):
        curr = self.consume()
        dt = curr.value
        if self.match('PERCENT'):
            attr = self.consume().value # TYPE or ROWTYPE
            dt += '%' + attr
        elif self.match('LPAREN'):
            size = self.consume('NUMBER_LIT').value
            if self.match('COMMA'):
                scale = self.consume('NUMBER_LIT').value
            self.consume('RPAREN')
        return dt

    def parse_block(self, is_create=False):
        decls = []
        if self.current().type == 'DECLARE' or is_create:
            if self.current().type == 'DECLARE':
                self.consume('DECLARE')
            while self.current().type not in ('BEGIN', 'EOF'):
                decls.append(self.parse_decl())
                
        self.consume('BEGIN')
        body = self.parse_statements()
        
        exceptions = []
        if self.match('EXCEPTION'):
            while self.current().type not in ('END', 'EOF'):
                if self.match('WHEN'):
                    exc_name = self.consume().value
                    self.consume('THEN')
                    exc_body = self.parse_statements()
                    exceptions.append((exc_name, exc_body))
                else:
                    break
                    
        self.consume('END')
        if self.current().type == 'ID':
            self.consume('ID') # Optional proc/func name after END
        self.match('SEMI')
        return Block(decls, body, exceptions)

    def parse_decl(self):
        if self.match('CURSOR'):
            name = self.consume('ID').value
            if self.match('LPAREN'):
                while self.current().type != 'RPAREN': self.consume()
                self.consume('RPAREN')
            self.consume('IS')
            
            # Capture SELECT statement until semicolon
            select_tokens = []
            while self.current().type not in ('SEMI', 'EOF'):
                select_tokens.append(self.consume().value)
            self.consume('SEMI')
            return CursorDecl(name, " ".join(select_tokens))
        else:
            name = self.consume('ID').value
            datatype = self.parse_datatype()
            init_expr = None
            if self.match('ASSIGN'):
                init_expr = self.parse_expr()
            self.consume('SEMI')
            return VarDecl(name, datatype, init_expr)

    def parse_statements(self):
        stmts = []
        while self.current().type not in ('END', 'EXCEPTION', 'WHEN', 'ELSIF', 'ELSE', 'EOF'):
            stmt = self.parse_statement()
            if stmt: stmts.append(stmt)
        return stmts

    def parse_statement(self):
        curr = self.current()
        if curr.type == 'IF': return self.parse_if()
        elif curr.type == 'CASE': return self.parse_case()
        elif curr.type == 'WHILE': return self.parse_while()
        elif curr.type == 'LOOP': return self.parse_basic_loop()
        elif curr.type == 'FOR': return self.parse_for()
        elif curr.type == 'EXIT': return self.parse_exit()
        elif curr.type == 'OPEN': return self.parse_open()
        elif curr.type == 'FETCH': return self.parse_fetch()
        elif curr.type == 'CLOSE': return self.parse_close()
        elif curr.type == 'SELECT': return self.parse_select_into()
        elif curr.type in ('INSERT', 'UPDATE', 'DELETE', 'COMMIT', 'ROLLBACK'): return self.parse_dml_stmt()
        elif curr.type == 'DBMS_OUTPUT': return self.parse_dbms_output()
        elif curr.type == 'RAISE': return self.parse_raise()
        elif curr.type == 'RETURN':
            self.consume('RETURN')
            expr = self.parse_expr()
            self.match('SEMI')
            return Assign('RETURN_VALUE', expr)
        elif curr.type == 'ID':
            # Could be assignment or procedure call
            peek = self.peek()
            if peek.type == 'ASSIGN':
                target = self.consume('ID').value
                self.consume('ASSIGN')
                expr = self.parse_expr()
                self.consume('SEMI')
                return Assign(target, expr)
            elif peek.type == 'DOT' or peek.type == 'PERCENT':
                # Could be record assignment or attribute
                var_tok = self.consume()
                target = var_tok.value
                while self.current().type in ('DOT', 'PERCENT'):
                    sep = self.consume().value
                    target += sep + self.consume().value
                if self.match('ASSIGN'):
                    expr = self.parse_expr()
                    self.consume('SEMI')
                    return Assign(target, expr)
                elif self.match('SEMI'):
                    return ProcCallStmt(target, [])
                elif self.match('LPAREN'):
                    args = []
                    if self.current().type != 'RPAREN':
                        args.append(self.parse_expr())
                        while self.match('COMMA'): args.append(self.parse_expr())
                    self.consume('RPAREN')
                    self.match('SEMI')
                    return ProcCallStmt(target, args)
            else:
                # Procedure call
                name = self.consume('ID').value
                args = []
                if self.match('LPAREN'):
                    if self.current().type != 'RPAREN':
                        args.append(self.parse_expr())
                        while self.match('COMMA'): args.append(self.parse_expr())
                    self.consume('RPAREN')
                self.consume('SEMI')
                return ProcCallStmt(name, args)
        else:
            self.consume()
            return None

    def parse_if(self):
        self.consume('IF')
        cond = self.parse_expr()
        self.consume('THEN')
        body = self.parse_statements()
        branches = [(cond, body)]
        
        while self.match('ELSIF'):
            cond = self.parse_expr()
            self.consume('THEN')
            body = self.parse_statements()
            branches.append((cond, body))
            
        else_body = []
        if self.match('ELSE'):
            else_body = self.parse_statements()
            
        self.consume('END')
        self.consume('IF')
        self.match('SEMI')
        return IfStmt(branches, else_body)

    def parse_case(self):
        self.consume('CASE')
        case_expr = None
        if self.current().type != 'WHEN':
            case_expr = self.parse_expr()
            
        branches = []
        while self.match('WHEN'):
            when_expr = self.parse_expr()
            self.consume('THEN')
            body = self.parse_statements()
            branches.append((when_expr, body))
            
        else_body = []
        if self.match('ELSE'):
            else_body = self.parse_statements()
            
        self.consume('END')
        self.consume('CASE')
        self.match('SEMI')
        return CaseStmt(case_expr, branches, else_body)

    def parse_while(self):
        self.consume('WHILE')
        cond = self.parse_expr()
        self.consume('LOOP')
        body = self.parse_statements()
        self.consume('END')
        self.consume('LOOP')
        self.match('SEMI')
        return WhileLoop(cond, body)

    def parse_basic_loop(self):
        self.consume('LOOP')
        body = self.parse_statements()
        self.consume('END')
        self.consume('LOOP')
        self.match('SEMI')
        return BasicLoop(body)

    def parse_exit(self):
        self.consume('EXIT')
        when_cond = None
        if self.match('WHEN'):
            when_cond = self.parse_expr()
        self.consume('SEMI')
        return ExitStmt(when_cond)

    def parse_for(self):
        self.consume('FOR')
        loop_var = self.consume('ID').value
        self.consume('IN')
        
        reverse = False
        if self.match('REVERSE'): reverse = True
        
        # Check if cursor for loop or numeric for loop
        if self.match('LPAREN'):
            # Cursor for loop with inline SELECT
            select_tokens = []
            while self.current().type != 'RPAREN':
                select_tokens.append(self.consume().value)
            self.consume('RPAREN')
            self.consume('LOOP')
            body = self.parse_statements()
            self.consume('END')
            self.consume('LOOP')
            self.match('SEMI')
            return CursorForLoop(loop_var, " ".join(select_tokens), body)
        else:
            # Could be cursor name or numeric range
            start_tok = self.parse_expr()
            if self.match('DOTDOT'):
                end_tok = self.parse_expr()
                self.consume('LOOP')
                body = self.parse_statements()
                self.consume('END')
                self.consume('LOOP')
                self.match('SEMI')
                return ForLoop(loop_var, start_tok, end_tok, reverse, body)
            else:
                # Cursor for loop with cursor name
                cursor_name = start_tok.name if isinstance(start_tok, Variable) else str(start_tok)
                self.consume('LOOP')
                body = self.parse_statements()
                self.consume('END')
                self.consume('LOOP')
                self.match('SEMI')
                return CursorForLoop(loop_var, cursor_name, body)

    def parse_open(self):
        self.consume('OPEN')
        cursor_name = self.consume('ID').value
        if self.match('LPAREN'):
            while self.current().type != 'RPAREN': self.consume()
            self.consume('RPAREN')
        self.consume('SEMI')
        return OpenStmt(cursor_name)

    def parse_fetch(self):
        self.consume('FETCH')
        cursor_name = self.consume('ID').value
        self.consume('INTO')
        target_vars = [self.consume('ID').value]
        while self.match('COMMA'):
            target_vars.append(self.consume('ID').value)
        self.consume('SEMI')
        return FetchStmt(cursor_name, target_vars)

    def parse_close(self):
        self.consume('CLOSE')
        cursor_name = self.consume('ID').value
        self.consume('SEMI')
        return CloseStmt(cursor_name)

    def parse_select_into(self):
        # We need to capture the SELECT query and extract the INTO clause
        select_tokens = ['SELECT']
        self.consume('SELECT')
        
        into_vars = []
        into_clause_str = ""
        
        while self.current().type not in ('SEMI', 'EOF'):
            if self.current().type == 'INTO':
                into_toks = [self.consume().value] # INTO
                into_vars.append(self.consume('ID').value)
                into_toks.append(into_vars[-1])
                while self.match('COMMA'):
                    into_vars.append(self.consume('ID').value)
                    into_toks.append(into_vars[-1])
                into_clause_str = " ".join(into_toks)
            else:
                select_tokens.append(self.consume().value)
                
        self.consume('SEMI')
        select_sql = " ".join(select_tokens)
        return SelectIntoStmt(select_sql, into_vars, into_clause_str)

    def parse_dml_stmt(self):
        tokens = []
        while self.current().type not in ('SEMI', 'EOF'):
            tokens.append(self.consume().value)
        self.consume('SEMI')
        return DmlStmt(" ".join(tokens))

    def parse_dbms_output(self):
        self.consume('DBMS_OUTPUT')
        self.consume('LPAREN')
        expr = self.parse_expr()
        self.consume('RPAREN')
        self.consume('SEMI')
        return DbmsOutputStmt(expr)

    def parse_raise(self):
        self.consume('RAISE')
        exc_name = self.consume().value
        self.consume('SEMI')
        return RaiseStmt(exc_name)

    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        node = self.parse_and()
        while self.current().type == 'OR':
            op = self.consume().value
            right = self.parse_and()
            node = BinaryOp(node, op, right)
        return node

    def parse_and(self):
        node = self.parse_equality()
        while self.current().type == 'AND':
            op = self.consume().value
            right = self.parse_equality()
            node = BinaryOp(node, op, right)
        return node

    def parse_equality(self):
        node = self.parse_relational()
        while self.current().type in ('EQ', 'NE', 'LIKE', 'BETWEEN'):
            op = self.consume().value
            right = self.parse_relational()
            node = BinaryOp(node, op, right)
        return node

    def parse_relational(self):
        node = self.parse_concat()
        while self.current().type in ('LT', 'GT', 'LE', 'GE'):
            op = self.consume().value
            right = self.parse_concat()
            node = BinaryOp(node, op, right)
        return node

    def parse_concat(self):
        node = self.parse_term()
        while self.current().type == 'CONCAT':
            op = self.consume().value
            right = self.parse_term()
            node = BinaryOp(node, op, right)
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.current().type in ('PLUS', 'MINUS'):
            op = self.consume().value
            right = self.parse_factor()
            node = BinaryOp(node, op, right)
        return node

    def parse_factor(self):
        node = self.parse_unary()
        while self.current().type in ('STAR', 'SLASH', 'MOD'):
            op = self.consume().value
            right = self.parse_unary()
            node = BinaryOp(node, op, right)
        return node

    def parse_unary(self):
        if self.current().type in ('PLUS', 'MINUS', 'NOT'):
            op = self.consume().value
            return UnaryOp(op, self.parse_unary())
        return self.parse_primary()

    def parse_primary(self):
        curr = self.current()
        if curr.type == 'NUMBER_LIT':
            val = self.consume().value
            return Literal(float(val) if '.' in val else int(val))
        elif curr.type == 'STRING_LIT':
            val = self.consume().value[1:-1] # Strip quotes
            return Literal(val)
        elif curr.type in ('TRUE', 'FALSE'):
            val = self.consume().value.upper() == 'TRUE'
            return Literal(val)
        elif curr.type == 'NULL':
            self.consume()
            return Literal(None)
        elif curr.type == 'LPAREN':
            self.consume('LPAREN')
            node = self.parse_expr()
            self.consume('RPAREN')
            return node
        elif curr.type == 'ID':
            peek = self.peek()
            if peek.type == 'PERCENT':
                id_tok = self.consume('ID')
                self.consume('PERCENT')
                attr = self.consume().value
                return CursorAttr(id_tok.value, attr)
            elif peek.type == 'LPAREN':
                func_name = self.consume('ID').value
                self.consume('LPAREN')
                args = []
                if self.current().type != 'RPAREN':
                    args.append(self.parse_expr())
                    while self.match('COMMA'):
                        args.append(self.parse_expr())
                self.consume('RPAREN')
                return FuncCall(func_name, args)
            else:
                var_name = self.consume('ID').value
                while self.current().type == 'DOT':
                    self.consume('DOT')
                    var_name += '.' + self.consume('ID').value
                return Variable(var_name)
        else:
            self.consume()
            return Literal(None)


# --- INTERPRETER / ENVIRONMENT ---

class LoopExit(Exception): pass
class PlsqlException(Exception):
    def __init__(self, exc_name, message):
        self.exc_name = exc_name.upper()
        self.message = message
        super().__init__(message)

class CursorObj:
    def __init__(self, select_sql):
        self.select_sql = select_sql
        self.rows = []
        self.rowcount = 0
        self.isopen = False
        self.found = None
        self.notfound = None

class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.vars = {}
        self.cursors = {}

    def define(self, name, value):
        self.vars[name.upper()] = value

    def assign(self, name, value):
        key = name.upper()
        if key in self.vars:
            self.vars[key] = value
            return
        if self.parent:
            self.parent.assign(name, value)
            return
        # If not found, define it in current scope
        self.vars[key] = value

    def get(self, name):
        key = name.upper()
        if key in self.vars:
            return self.vars[key]
        if self.parent:
            return self.parent.get(name)
        return None

    def get_all_vars(self):
        all_vars = {}
        if self.parent:
            all_vars.update(self.parent.get_all_vars())
        all_vars.update(self.vars)
        return all_vars

    def define_cursor(self, name, cursor_obj):
        self.cursors[name.upper()] = cursor_obj

    def get_cursor(self, name):
        key = name.upper()
        if key in self.cursors:
            return self.cursors[key]
        if self.parent:
            return self.parent.get_cursor(name)
        raise RuntimeError(f"Cursor '{name}' not declared")


class Interpreter:
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.dbms_output = []
        self.env = Environment()

    def prep_sql(self, sql, env_vars):
        """Replaces bare PL/SQL variable names in SQL with named parameter placeholders :var."""
        # Sort by length descending to avoid partial matches
        sorted_vars = sorted(env_vars.keys(), key=len, reverse=True)
        # Prevent replacing inside quotes
        parts = re.split(r"('[^']*')", sql)
        for i in range(0, len(parts), 2):
            for v in sorted_vars:
                # Replace whole word match of variable name with :var
                parts[i] = re.sub(r'\b' + re.escape(v) + r'\b', f':{v}', parts[i], flags=re.IGNORECASE)
        return "".join(parts)

    def execute(self, code):
        self.dbms_output = []
        tokens = tokenize(code)
        parser = Parser(tokens, code)
        program = parser.parse()
        
        try:
            for stmt in program.statements:
                self.eval(stmt, self.env)
            return {
                'status': 'success',
                'dbms_output': self.dbms_output,
                'message': 'PL/SQL block executed successfully.'
            }
        except PlsqlException as pe:
            return {
                'status': 'error',
                'dbms_output': self.dbms_output,
                'message': f"ORA-06516: PL/SQL Unhandled Exception: {pe.exc_name} - {pe.message}"
            }
        except Exception as e:
            return {
                'status': 'error',
                'dbms_output': self.dbms_output,
                'message': f"Error: {str(e)}"
            }

    def eval(self, node, env):
        if node is None: return None
        
        if isinstance(node, Program):
            for stmt in node.statements: self.eval(stmt, env)
            return
            
        elif isinstance(node, Block):
            block_env = Environment(parent=env)
            for decl in node.decls:
                self.eval(decl, block_env)
            try:
                for stmt in node.body:
                    self.eval(stmt, block_env)
            except PlsqlException as pe:
                # Check exceptions
                handled = False
                for exc_name, exc_body in node.exceptions:
                    if exc_name.upper() == pe.exc_name or exc_name.upper() == 'OTHERS':
                        for s in exc_body: self.eval(s, block_env)
                        handled = True
                        break
                if not handled:
                    raise pe
            return

        elif isinstance(node, VarDecl):
            val = self.eval(node.init_expr, env) if node.init_expr else None
            env.define(node.name, val)
            return

        elif isinstance(node, CursorDecl):
            env.define_cursor(node.name, CursorObj(node.select_sql))
            return

        elif isinstance(node, Assign):
            val = self.eval(node.expr, env)
            env.assign(node.target, val)
            if node.target.upper() == 'RETURN_VALUE':
                # Store return value in environment
                env.define('RETURN_VALUE', val)
            return

        elif isinstance(node, IfStmt):
            for cond_expr, body_stmts in node.branches:
                if self.eval(cond_expr, env):
                    for s in body_stmts: self.eval(s, env)
                    return
            for s in node.else_body: self.eval(s, env)
            return

        elif isinstance(node, CaseStmt):
            case_val = self.eval(node.case_expr, env) if node.case_expr else None
            for when_expr, body_stmts in node.branches:
                when_val = self.eval(when_expr, env)
                if case_val is not None:
                    if case_val == when_val:
                        for s in body_stmts: self.eval(s, env)
                        return
                else:
                    if when_val:
                        for s in body_stmts: self.eval(s, env)
                        return
            for s in node.else_body: self.eval(s, env)
            return

        elif isinstance(node, WhileLoop):
            while self.eval(node.cond, env):
                try:
                    for s in node.body: self.eval(s, env)
                except LoopExit:
                    break
            return

        elif isinstance(node, BasicLoop):
            while True:
                try:
                    for s in node.body: self.eval(s, env)
                except LoopExit:
                    break
            return

        elif isinstance(node, ExitStmt):
            if node.when_cond is None or self.eval(node.when_cond, env):
                raise LoopExit()
            return

        elif isinstance(node, ForLoop):
            start_val = int(self.eval(node.start_expr, env))
            end_val = int(self.eval(node.end_expr, env))
            range_iter = range(end_val, start_val - 1, -1) if node.reverse else range(start_val, end_val + 1)
            
            loop_env = Environment(parent=env)
            for i in range_iter:
                loop_env.define(node.loop_var, i)
                try:
                    for s in node.body: self.eval(s, loop_env)
                except LoopExit:
                    break
            return

        elif isinstance(node, CursorForLoop):
            # Check if it's an inline query or declared cursor
            if node.cursor_name.upper().startswith('SELECT '):
                select_sql = node.cursor_name
            else:
                cur_obj = env.get_cursor(node.cursor_name)
                select_sql = cur_obj.select_sql
                
            env_vars = env.get_all_vars()
            prep_sql = self.prep_sql(select_sql, env_vars)
            
            cursor = self.db_conn.cursor()
            cursor.execute(prep_sql, env_vars)
            rows = cursor.fetchall()
            
            loop_env = Environment(parent=env)
            for row in rows:
                # Define record object as dict
                row_dict = dict(row)
                loop_env.define(node.loop_var, row_dict)
                # Also define individual properties like rec.empno
                for col_name, col_val in row_dict.items():
                    loop_env.define(f"{node.loop_var}.{col_name}", col_val)
                try:
                    for s in node.body: self.eval(s, loop_env)
                except LoopExit:
                    break
            return

        elif isinstance(node, OpenStmt):
            cur_obj = env.get_cursor(node.cursor_name)
            env_vars = env.get_all_vars()
            prep_sql = self.prep_sql(cur_obj.select_sql, env_vars)
            
            cursor = self.db_conn.cursor()
            cursor.execute(prep_sql, env_vars)
            cur_obj.rows = [dict(r) for r in cursor.fetchall()]
            cur_obj.isopen = True
            cur_obj.rowcount = 0
            cur_obj.found = None
            cur_obj.notfound = None
            return

        elif isinstance(node, FetchStmt):
            cur_obj = env.get_cursor(node.cursor_name)
            if not cur_obj.isopen:
                raise RuntimeError(f"ORA-01001: invalid cursor '{node.cursor_name}' (not open)")
                
            if cur_obj.rowcount < len(cur_obj.rows):
                row = cur_obj.rows[cur_obj.rowcount]
                cur_obj.rowcount += 1
                cur_obj.found = True
                cur_obj.notfound = False
                
                # Assign to target vars
                keys = list(row.keys())
                for i, var_name in enumerate(node.target_vars):
                    if i < len(keys):
                        env.assign(var_name, row[keys[i]])
            else:
                cur_obj.found = False
                cur_obj.notfound = True
            return

        elif isinstance(node, CloseStmt):
            cur_obj = env.get_cursor(node.cursor_name)
            cur_obj.isopen = False
            return

        elif isinstance(node, SelectIntoStmt):
            env_vars = env.get_all_vars()
            prep_sql = self.prep_sql(node.select_sql, env_vars)
            
            cursor = self.db_conn.cursor()
            cursor.execute(prep_sql, env_vars)
            rows = cursor.fetchall()
            
            if len(rows) == 0:
                raise PlsqlException('NO_DATA_FOUND', 'ORA-01403: no data found')
            elif len(rows) > 1:
                raise PlsqlException('TOO_MANY_ROWS', 'ORA-01422: exact fetch returns more than requested number of rows')
                
            row = dict(rows[0])
            keys = list(row.keys())
            for i, var_name in enumerate(node.target_vars):
                if i < len(keys):
                    env.assign(var_name, row[keys[i]])
            return

        elif isinstance(node, DmlStmt):
            env_vars = env.get_all_vars()
            prep_sql = self.prep_sql(node.sql, env_vars)
            cursor = self.db_conn.cursor()
            cursor.execute(prep_sql, env_vars)
            self.db_conn.commit()
            return

        elif isinstance(node, DbmsOutputStmt):
            val = self.eval(node.expr, env)
            self.dbms_output.append(str(val) if val is not None else '')
            return

        elif isinstance(node, RaiseStmt):
            raise PlsqlException(node.exc_name, f"User-defined exception '{node.exc_name}' raised")

        elif isinstance(node, CreateProcStmt):
            cursor = self.db_conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO user_source (name, type, text) VALUES (?, ?, ?)",
                (node.name.upper(), 'FUNCTION' if node.is_function else 'PROCEDURE', node.raw_text)
            )
            self.db_conn.commit()
            self.dbms_output.append(f"{'Function' if node.is_function else 'Procedure'} {node.name.upper()} created/updated.")
            return

        elif isinstance(node, ProcCallStmt):
            # Fetch proc from user_source
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT text, type FROM user_source WHERE name = ?", (node.name.upper(),))
            row = cursor.fetchone()
            if not row:
                # Might be a built-in or undefined
                raise RuntimeError(f"PLS-00201: identifier '{node.name}' must be declared")
                
            proc_code = row['text']
            proc_tokens = tokenize(proc_code)
            proc_parser = Parser(proc_tokens, proc_code)
            proc_ast = proc_parser.parse_create_stmt()
            
            call_env = Environment(parent=env)
            # Bind args to params
            for i, (p_name, p_type) in enumerate(proc_ast.params):
                arg_val = self.eval(node.args[i], env) if i < len(node.args) else None
                call_env.define(p_name, arg_val)
                
            # Execute body
            self.eval(proc_ast.body, call_env)
            return

        elif isinstance(node, FuncCall):
            # Check if built-in Python/SQLite func
            func_name = node.name.upper()
            args_eval = [self.eval(arg, env) for arg in node.args]
            
            if func_name == 'NVL': return db._nvl(*args_eval)
            elif func_name == 'NVL2': return db._nvl2(*args_eval)
            elif func_name == 'CONCAT': return db._concat(*args_eval)
            elif func_name == 'TO_CHAR': return db._to_char(*args_eval)
            elif func_name == 'TO_DATE': return db._to_date(*args_eval)
            elif func_name == 'TO_NUMBER': return db._to_number(*args_eval)
            elif func_name == 'TRUNC': return db._trunc(*args_eval)
            elif func_name == 'MOD': return db._mod(*args_eval)
            elif func_name == 'INITCAP': return db._initcap(*args_eval)
            elif func_name == 'LPAD': return db._lpad(*args_eval)
            elif func_name == 'RPAD': return db._rpad(*args_eval)
            elif func_name == 'UPPER': return str(args_eval[0]).upper() if args_eval[0] else None
            elif func_name == 'LOWER': return str(args_eval[0]).lower() if args_eval[0] else None
            elif func_name == 'LENGTH': return len(str(args_eval[0])) if args_eval[0] else None
            elif func_name == 'SYSDATE': return db._sysdate()
            elif func_name == 'SYSTIMESTAMP': return db._systimestamp()
            
            # Otherwise check user_source for custom function
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT text FROM user_source WHERE name = ? AND type = 'FUNCTION'", (func_name,))
            row = cursor.fetchone()
            if not row:
                raise RuntimeError(f"PLS-00201: function '{node.name}' must be declared")
                
            func_code = row['text']
            func_tokens = tokenize(func_code)
            func_parser = Parser(func_tokens, func_code)
            func_ast = func_parser.parse_create_stmt()
            
            call_env = Environment(parent=env)
            for i, (p_name, p_type) in enumerate(func_ast.params):
                arg_val = args_eval[i] if i < len(args_eval) else None
                call_env.define(p_name, arg_val)
                
            self.eval(func_ast.body, call_env)
            return call_env.get('RETURN_VALUE')

        elif isinstance(node, BinaryOp):
            left = self.eval(node.left, env)
            right = self.eval(node.right, env)
            op = node.op.upper()
            
            if op == '+': return (left or 0) + (right or 0)
            elif op == '-': return (left or 0) - (right or 0)
            elif op == '*': return (left or 0) * (right or 0)
            elif op == '/': return (left or 0) / (right or 0)
            elif op == 'MOD': return (left or 0) % (right or 0)
            elif op == '||': return f"{left or ''}{right or ''}"
            elif op == '=': return left == right
            elif op in ('!=', '<>'): return left != right
            elif op == '<': return left < right if left is not None and right is not None else False
            elif op == '>': return left > right if left is not None and right is not None else False
            elif op == '<=': return left <= right if left is not None and right is not None else False
            elif op == '>=': return left >= right if left is not None and right is not None else False
            elif op == 'AND': return bool(left) and bool(right)
            elif op == 'OR': return bool(left) or bool(right)
            elif op == 'LIKE':
                if left is None or right is None: return False
                pattern = "^" + re.escape(str(right)).replace(r'\%', '.*').replace(r'\_', '.') + "$"
                return bool(re.match(pattern, str(left), re.IGNORECASE))
            return None

        elif isinstance(node, UnaryOp):
            val = self.eval(node.expr, env)
            if node.op.upper() == '-': return -val
            elif node.op.upper() == 'NOT': return not val
            return val

        elif isinstance(node, Literal):
            return node.value

        elif isinstance(node, Variable):
            return env.get(node.name)

        elif isinstance(node, CursorAttr):
            cur_obj = env.get_cursor(node.cursor_name)
            attr = node.attr.upper()
            if attr == 'FOUND': return cur_obj.found
            elif attr == 'NOTFOUND': return cur_obj.notfound
            elif attr == 'ROWCOUNT': return cur_obj.rowcount
            elif attr == 'ISOPEN': return cur_obj.isopen
            return None

def execute_plsql(code):
    conn = db.get_connection()
    interpreter = Interpreter(conn)
    result = interpreter.execute(code)
    conn.close()
    return result
