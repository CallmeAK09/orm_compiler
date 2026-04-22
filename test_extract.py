import os
import django
from django.conf import settings
from django.db import models

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orm_compiler.settings')
django.setup()

temp_models_code = """
class Publisher(models.Model):
    name = models.CharField(max_length=100)
    class Meta:
        app_label = 'compiler'
"""

env = {'models': models}
exec(temp_models_code, env)

for name, obj in env.items():
    if isinstance(obj, type) and issubclass(obj, models.Model) and obj is not models.Model:
        print(f"Model: {name}")
        fields = [f.name for f in obj._meta.fields]
        print(f"Fields: {fields}")
