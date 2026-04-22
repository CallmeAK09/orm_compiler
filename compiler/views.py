import json
import traceback
import contextlib
import io
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.apps import apps
from django.db import models
from django.core.serializers import serialize
from .models import Author, Book, Library
from .sandbox import validate_code


def serialize_value(val):
    """
    Convert a field value to a JSON-safe string for display in the table.
    date/datetime → ISO string  e.g. "1997-06-26"
    Decimal, UUID, and anything else non-serializable → str()
    """
    import datetime
    from decimal import Decimal
    import uuid

    if val is None:
        return None
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, (datetime.datetime,)):
        return val.strftime('%Y-%m-%d %H:%M')   # e.g. "2024-01-15 09:30"
    if isinstance(val, datetime.date):
        return val.strftime('%Y-%m-%d')          # e.g. "1997-06-26"
    if isinstance(val, (Decimal, uuid.UUID)):
        return str(val)
    # For everything else try native JSON; fall back to str()
    try:
        json.dumps(val)
        return val
    except (TypeError, ValueError):
        return str(val)


def get_record_dict(instance, model):
    """
    Build a display-friendly dict for a single model instance.
    - ForeignKey fields: show  id + __str__ of the related object  e.g. "1 — J.K. Rowling"
    - ManyToMany fields: comma-separated __str__ values
    - All other fields: raw value
    """
    record = {}

    # --- Regular fields (including FK id columns) ---
    for field in model._meta.fields:
        val = getattr(instance, field.attname)   # attname gives  author_id  not  author
        record[field.name] = serialize_value(val)

        # For FK fields also add a human-readable column  author__name
        if isinstance(field, models.ForeignKey):
            try:
                related_obj = getattr(instance, field.name)
                if related_obj is not None:
                    record[field.name + '__str'] = str(related_obj)
                else:
                    record[field.name + '__str'] = None
            except Exception:
                record[field.name + '__str'] = None

    # --- ManyToMany fields ---
    for field in model._meta.many_to_many:
        try:
            related_qs = getattr(instance, field.name).all()
            record[field.name] = ', '.join(str(obj) for obj in related_qs) or '—'
        except Exception:
            record[field.name] = '—'

    return record


def get_field_names(model):
    """
    Return the ordered list of column headers for a model, inserting
    FK __str__ columns right after their FK id column.
    """
    columns = []
    for field in model._meta.fields:
        columns.append(field.name)
        if isinstance(field, models.ForeignKey):
            columns.append(field.name + '__str')   # human-readable companion column

    for field in model._meta.many_to_many:
        columns.append(field.name)

    return columns


def get_tables_data(env=None):
    tables_data = []

    for model in [Author, Book, Library]:
        instances = model.objects.select_related().prefetch_related(
            *[f.name for f in model._meta.many_to_many]
        ).all()[:10]

        tables_data.append({
            'name': model.__name__,
            'fields': get_field_names(model),
            'records': [get_record_dict(inst, model) for inst in instances]
        })

    if env:
        for name, obj in env.items():
            if obj in [Author, Book, Library]:
                continue
            if isinstance(obj, type) and issubclass(obj, models.Model) and obj is not models.Model:
                from django.db import connection

                table_name = obj._meta.db_table

                if table_name not in connection.introspection.table_names():
                    with connection.schema_editor() as schema_editor:
                        schema_editor.create_model(obj)

                    # 👉 INSERT ONE ROW so it appears in UI
                    try:
                        obj.objects.create()
                    except Exception:
                        pass

                try:
                    instances = obj.objects.select_related().prefetch_related(
                        *[f.name for f in obj._meta.many_to_many]
                    ).all()[:10]
                    records = [get_record_dict(inst, obj) for inst in instances]
                except Exception:
                    records = []

                tables_data.append({
                    'name': name + ' (Custom)',
                    'fields': get_field_names(obj),
                    'records': records
                })

    return tables_data


def reset_default_tables():
    from django.db import connection

    # Reset tables (PostgreSQL)
    with connection.cursor() as cursor:
        cursor.execute("""
            TRUNCATE TABLE
            compiler_library_books,
            compiler_library,
            compiler_book,
            compiler_author
            RESTART IDENTITY CASCADE;
        """)

    # Authors
    a1 = Author.objects.create(
        name='J.K. Rowling',
        email='jk@example.com',
        bio='British author best known for the Harry Potter series.'
    )

    a2 = Author.objects.create(
        name='George R.R. Martin',
        email='grrm@example.com',
        bio='American novelist famous for A Song of Ice and Fire.'
    )

    a3 = Author.objects.create(
        name='J.R.R. Tolkien',
        email='jrrt@example.com',
        bio='English writer known for The Hobbit and The Lord of the Rings.'
    )

    a4 = Author.objects.create(
        name='Stephen King',
        email='sking@example.com',
        bio='American author renowned for horror and supernatural fiction.'
    )

    a5 = Author.objects.create(
        name='Agatha Christie',
        email='agatha@example.com',
        bio='English writer celebrated for her detective and mystery novels.'
    )

    # Books (FK → Author)
    b1 = Book.objects.create(title='Harry Potter',              isbn='9780747532699', author=a1, pages=223, published_date='1997-06-26', language='English')
    b2 = Book.objects.create(title='Game of Thrones',           isbn='9780553103540', author=a2, pages=694, published_date='1996-08-01', language='English')
    b3 = Book.objects.create(title='The Hobbit',                isbn='9780261102217', author=a3, pages=310, published_date='1937-09-21', language='English')
    b4 = Book.objects.create(title='The Shining',               isbn='9780385121675', author=a4, pages=447, published_date='1977-01-28', language='English')
    b5 = Book.objects.create(title='And Then There Were None',  isbn='9780007136834', author=a2, pages=272, published_date='1939-11-06', language='English')

    # Libraries (M2M ↔ Book)
    l1 = Library.objects.create(name='Central Library',    location='New York',  established_date='1895-03-15')
    l2 = Library.objects.create(name='Community Library',  location='London',    established_date='1922-07-04')
    l3 = Library.objects.create(name='University Library', location='Boston',    established_date='1948-09-01')
    l4 = Library.objects.create(name='State Library',      location='Sydney',    established_date='1869-11-20')
    l5 = Library.objects.create(name='National Library',   location='Toronto',   established_date='1953-05-12')

    l1.books.set([b1, b2, b3])
    l2.books.set([b3, b5, b1])
    l3.books.set([b4, b1])
    l4.books.set([b2, b3])
    l5.books.set([b5, b4])


def index(request):
    if not request.session.get('db_initialized', False):
        reset_default_tables()
        request.session['db_initialized'] = True

    env = None
    temp_models_code = request.session.get('temp_models_code', '')

    if temp_models_code:
        temp_models_code = inject_app_label(temp_models_code)

    if temp_models_code:
        env = {
            'models': models,
            '__name__': 'compiler.models'
        }
        try:
            exec(temp_models_code, env)
        except Exception:
            pass

    tables_data = get_tables_data(env)

    context = {
        'tables_data': tables_data,
        'temp_models_code': temp_models_code
    }
    return render(request, 'compiler.html', context)

def inject_app_label(code):
    lines = code.split('\n')
    new_lines = []
    inside_model = False
    indent = ""

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect model class
        if stripped.startswith("class ") and "models.Model" in stripped:
            inside_model = True
            indent = line[:len(line) - len(line.lstrip())] + "    "
            new_lines.append(line)
            continue

        # If inside model and Meta already exists → skip injection
        if inside_model and stripped.startswith("class Meta"):
            inside_model = False  # assume user handled it
            new_lines.append(line)
            continue

        # End of class (next class or empty line)
        if inside_model and (stripped.startswith("class ") or stripped == ""):
            # Inject Meta before leaving
            new_lines.append(indent + "class Meta:")
            new_lines.append(indent + "    app_label = 'compiler'")
            inside_model = False

        new_lines.append(line)

    # Edge case: file ends while still inside model
    if inside_model:
        new_lines.append(indent + "class Meta:")
        new_lines.append(indent + "    app_label = 'compiler'")

    return "\n".join(new_lines)

def save_models(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            models_code = inject_app_label(data.get('models_code', ''))

            is_valid, msg = validate_code(models_code)
            if not is_valid:
                return JsonResponse({'status': 'error', 'output': msg})

            request.session['temp_models_code'] = models_code
            request.session.modified = True

            # ✅ INCLUDE DEFAULT MODELS
            env = {
                'models': models,
                'Author': Author,
                'Book': Book,
                'Library': Library,
                '__name__': 'compiler.models'
            }

            exec(models_code, env)

            tables_data = get_tables_data(env)

            return JsonResponse({
                'status': 'success',
                'message': 'Models saved successfully.',
                'tables_data': tables_data
            })

        except Exception:
            return JsonResponse({'status': 'error', 'output': traceback.format_exc()})


def execute_query(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query_code = data.get('query', '')

            env = {
                'Author':  Author,
                'Book':    Book,
                'Library': Library,
                'models':  models,
                '__name__': 'compiler.models'
            }

            is_valid, msg = validate_code(query_code)
            if not is_valid:
                return JsonResponse({'status': 'error', 'output': msg})

            temp_models_code = request.session.get('temp_models_code', '')
            if temp_models_code:
                exec(temp_models_code, env)

            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                try:
                    result = eval(query_code, env)
                    if result is not None:
                        print(result)
                except SyntaxError:
                    exec(query_code, env)

            output = output_buffer.getvalue()
            tables_data = get_tables_data(env)
            return JsonResponse({'status': 'success', 'output': output, 'tables_data': tables_data})

        except Exception:
            return JsonResponse({'status': 'error', 'output': traceback.format_exc()})

    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


def reset_session(request):
    request.session.flush()
    request.session.create()
    return redirect('dashboard')