import os
import django
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
import contextlib

# Configure minimal Django settings
if not settings.configured:
    settings.configure(
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
        INSTALLED_APPS=['compiler'],
    )
    django.setup()

# Define a model for testing
class TestModel(models.Model):
    name = models.CharField(max_length=5)
    class Meta:
        app_label = 'compiler'

# The monkey-patch logic from views.py
@contextlib.contextmanager
def enforced_validation():
    original_save = models.Model.save
    def validated_save(self, *args, **kwargs):
        self.full_clean()
        return original_save(self, *args, **kwargs)
    models.Model.save = validated_save
    try:
        yield
    finally:
        models.Model.save = original_save

def test_validation():
    # Setup database
    from django.db import connection
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(TestModel)

    print("Testing with validation enforced...")
    with enforced_validation():
        try:
            # This should fail because name is too long
            TestModel.objects.create(name="TooLong")
            print("❌ Error: Should have raised ValidationError")
        except ValidationError as e:
            print(f"✅ Success: Caught expected ValidationError: {e}")

    print("\nTesting without validation enforced...")
    try:
        # This might succeed or fail depending on DB-level constraints.
        # SQLite usually doesn't enforce CharField max_length at the DB level by default in Django.
        obj = TestModel.objects.create(name="TooLong")
        print(f"✅ Note: Saved '{obj.name}' without validation (expected for SQLite/Django default)")
    except Exception as e:
        print(f"ℹ️ Note: Caught exception without enforcement: {e}")

if __name__ == "__main__":
    test_validation()
