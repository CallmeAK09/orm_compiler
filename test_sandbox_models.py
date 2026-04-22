import ast
from compiler.sandbox import validate_code

valid_model = """
class TestPublisher(models.Model):
    name = models.CharField(max_length=100)
"""
print("Valid model:", validate_code(valid_model))

malicious_model = """
class TestPublisher(models.Model):
    name = models.CharField(max_length=100)
    def save(self, *args, **kwargs):
        import os
        os.system('rm -rf /')
"""
print("Malicious model:", validate_code(malicious_model))

