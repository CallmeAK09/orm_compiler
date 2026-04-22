import ast
from compiler.sandbox import validate_code

valid_query = "Author.objects.all()"
print("Valid:", validate_code(valid_query))

malicious_import = "import os; os.system('rm -rf /')"
print("Import:", validate_code(malicious_import))

malicious_dunder = "Author.__class__"
print("Dunder:", validate_code(malicious_dunder))

malicious_raw = "Author.objects.raw('DROP TABLE compiler_author')"
print("Raw SQL:", validate_code(malicious_raw))

