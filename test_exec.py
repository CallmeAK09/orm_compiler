import os
import django
from django.conf import settings
from django.db import models, connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orm_compiler.settings')
django.setup()

models_code = """
class TestPublisher(models.Model):
    name = models.CharField(max_length=100)
"""

env = {
    'models': models,
    '__name__': 'compiler.models'
}

exec(models_code, env)

for name, obj in env.items():
    if isinstance(obj, type) and issubclass(obj, models.Model) and obj is not models.Model:
        print("Found model:", name)
        try:
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(obj)
        except Exception as e:
            print("Create table error:", e)
        
        obj.objects.create(name='Test 1')
        print(list(obj.objects.all().values()))
