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

def get_tables_data(env=None):
    tables_data = []
    for model in [Author, Book, Library]:
        records = model.objects.all()
        tables_data.append({
            'name': model.__name__,
            'fields': [f.name for f in model._meta.fields],
            'records': list(records.values())[:10]
        })
        
    if env:
        for name, obj in env.items():
            if obj in [Author, Book, Library]:
                continue
            if isinstance(obj, type) and issubclass(obj, models.Model) and obj is not models.Model:
                from django.db import connection
                with connection.schema_editor() as schema_editor:
                    try:
                        schema_editor.create_model(obj)
                    except Exception:
                        pass # Table might already exist
                        
                fields = [f.name for f in obj._meta.fields]
                try:
                    records = list(obj.objects.all().values())[:10]
                except Exception:
                    records = []
                tables_data.append({
                    'name': name + ' (Custom)',
                    'fields': fields,
                    'records': records
                })
    return tables_data

def reset_default_tables():
    from django.db import connection
    
    # Clear existing data and reset PostgreSQL auto-increment sequences
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE compiler_library, compiler_book, compiler_author, compiler_library_books RESTART IDENTITY CASCADE;")
    
    # Insert 5 records for each
    a1 = Author.objects.create(name='J.K. Rowling', email='jk@example.com', bio='British author')
    a2 = Author.objects.create(name='George R.R. Martin', email='grrm@example.com', bio='American novelist')
    a3 = Author.objects.create(name='J.R.R. Tolkien', email='jrrt@example.com', bio='English writer')
    a4 = Author.objects.create(name='Stephen King', email='sking@example.com', bio='American author of horror')
    a5 = Author.objects.create(name='Agatha Christie', email='agatha@example.com', bio='English detective novelist')
    
    b1 = Book.objects.create(title='Harry Potter', isbn='9780747532699', author=a1, pages=223)
    b2 = Book.objects.create(title='Game of Thrones', isbn='9780553103540', author=a2, pages=694)
    b3 = Book.objects.create(title='The Hobbit', isbn='9780261102217', author=a3, pages=310)
    b4 = Book.objects.create(title='The Shining', isbn='9780385121675', author=a4, pages=447)
    b5 = Book.objects.create(title='And Then There Were None', isbn='9780007136834', author=a5, pages=272)
    
    l1 = Library.objects.create(name='Central Library', location='New York')
    l1.books.add(b1, b2)
    l2 = Library.objects.create(name='Community Library', location='London')
    l2.books.add(b3, b5)
    l3 = Library.objects.create(name='University Library', location='Boston')
    l3.books.add(b4, b1)
    l4 = Library.objects.create(name='State Library', location='Sydney')
    l4.books.add(b2, b3)
    l5 = Library.objects.create(name='National Library', location='Toronto')
    l5.books.add(b5, b4)

def index(request):
    """
    Renders the main page.
    Passes available standard models and their data.
    """
    if not request.session.get('db_initialized', False):
        reset_default_tables()
        request.session['db_initialized'] = True

    env = None
    temp_models_code = request.session.get('temp_models_code', '')
    
    if temp_models_code:
        env = {
            'models': models,
            '__name__': 'compiler.models'  # trick django into using 'compiler' as app_label
        }
        try:
            exec(temp_models_code, env)
        except Exception:
            pass # ignore errors here, they are shown when saving

    tables_data = get_tables_data(env)

    context = {
        'tables_data': tables_data,
        'temp_models_code': temp_models_code
    }
    return render(request, 'compiler.html', context)

def save_models(request):
    """
    Saves the temporary model code to the session after evaluating it.
    Returns the updated tables_data.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        models_code = data.get('models_code', '')
        
        env = {
            'models': models,
            '__name__': 'compiler.models'
        }
        try:
            # Pre-validate AST syntax for malicious code
            is_valid, msg = validate_code(models_code)
            if not is_valid:
                return JsonResponse({'status': 'error', 'output': msg})
                
            # Validate the code by executing it
            exec(models_code, env)
            request.session['temp_models_code'] = models_code
            
            # Extract models to return dynamically
            tables_data = get_tables_data(env)
            
            return JsonResponse({'status': 'success', 'message': 'Models validated and saved.', 'tables_data': tables_data})
        except Exception as e:
            # Return error trace if code fails
            error_details = traceback.format_exc()
            return JsonResponse({'status': 'error', 'output': error_details})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

def execute_query(request):
    """
    Executes the ORM query safely.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query_code = data.get('query', '')
            
            # Setup environment with standard models
            env = {
                'Author': Author,
                'Book': Book,
                'Library': Library,
                'models': models,
                '__name__': 'compiler.models'
            }
            
            # Pre-validate AST syntax for malicious query code
            is_valid, msg = validate_code(query_code)
            if not is_valid:
                return JsonResponse({'status': 'error', 'output': msg})
            
            # Include temp models code if any
            temp_models_code = request.session.get('temp_models_code', '')
            if temp_models_code:
                exec(temp_models_code, env)
            
            # Capture standard output and evaluate query
            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                # We try to evaluate as an expression first
                try:
                    result = eval(query_code, env)
                    if hasattr(result, 'query'):
                        # If it's a QuerySet, evaluate it to a list
                        result = list(result)
                    
                    if result is not None:
                        print(result)
                except SyntaxError:
                    # If it's not an expression, we try to exec it as a statement
                    exec(query_code, env)
            
            output = output_buffer.getvalue()
            tables_data = get_tables_data(env)
            return JsonResponse({'status': 'success', 'output': output, 'tables_data': tables_data})
            
        except Exception as e:
            # Capture full traceback for the terminal
            error_details = traceback.format_exc()
            return JsonResponse({'status': 'error', 'output': error_details})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

def reset_session(request):
    """
    Clears the session completely so that the user gets a fresh DB next time.
    """
    request.session.flush()
    return redirect('dashboard')
