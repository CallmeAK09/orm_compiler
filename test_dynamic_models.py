import os
import django
from django.conf import settings
from django.db import models, connection
from django.core.management.color import no_style

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orm_compiler.settings')
django.setup()

def create_dynamic_model(name, fields, app_label='compiler'):
    class Meta:
        pass
    setattr(Meta, 'app_label', app_label)
    
    attrs = {'__module__': __name__, 'Meta': Meta}
    attrs.update(fields)
    
    model = type(name, (models.Model,), attrs)
    
    with connection.schema_editor() as schema_editor:
        try:
            schema_editor.create_model(model)
        except Exception as e:
            print(f"Already exists or error: {e}")
            
    return model

# Test
fields = {
    'name': models.CharField(max_length=100),
    'age': models.IntegerField()
}

Person = create_dynamic_model('Person', fields)
Person.objects.create(name='John Doe', age=30)
print("Persons:", Person.objects.all().values())
