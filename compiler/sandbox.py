import ast

BANNED_FUNCTIONS = {
    'open', 'eval', 'exec', '__import__', 'getattr', 'setattr', 
    'globals', 'locals', 'compile', 'input', 'breakpoint'
}

BANNED_ATTRIBUTES = {
    'raw', 'execute' # Prevent raw SQL execution
}

class SecurityException(Exception):
    pass

class ASTValidator(ast.NodeVisitor):
    def visit_Import(self, node):
        raise SecurityException("Importing modules is not allowed for security reasons.")
        
    def visit_ImportFrom(self, node):
        raise SecurityException("Importing from modules is not allowed for security reasons.")
        
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in BANNED_FUNCTIONS:
                raise SecurityException(f"The use of the '{node.func.id}' function is blocked.")
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        if node.attr.startswith('__'):
            raise SecurityException("Accessing dunder (magic) attributes is strictly blocked.")
        if node.attr in BANNED_ATTRIBUTES:
            raise SecurityException(f"The use of the '{node.attr}' method is blocked to prevent raw SQL execution.")
        self.generic_visit(node)
        
def validate_code(code_string):
    try:
        tree = ast.parse(code_string)
        validator = ASTValidator()
        validator.visit(tree)
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"
    except SecurityException as e:
        return False, f"Security Block: {e}"
    except Exception as e:
        return False, f"Validation Error: {e}"
