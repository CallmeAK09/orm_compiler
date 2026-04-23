import os
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orm_compiler.settings')
django.setup()

from compiler.models import Author, Book, Library
from django.db import models, connection

def test_aggregates():
    print("--- Testing Aggregates ---")
    try:
        from django.db.models import Count, Avg, Max, Min, Sum
        # Count is often used directly or via aggregate
        res = Book.objects.aggregate(total_pages=Sum('pages'), avg_pages=Avg('pages'))
        print(f"Aggregate result: {res}")
        
        # Test count() method
        count = Author.objects.count()
        print(f"Author count: {count}")

        # Test exists()
        exists = Author.objects.filter(name='J.K. Rowling').exists()
        print(f"J.K. Rowling exists: {exists}")

    except Exception as e:
        print(f"Aggregate error: {e}")

def test_raw_query():
    print("\n--- Testing Raw Query ---")
    try:
        raw_res = Author.objects.raw('SELECT * FROM compiler_author')
        print(f"Raw query type: {type(raw_res)}")
        for author in list(raw_res)[:2]:
            print(f"Author from raw: {author.name}")
    except Exception as e:
        print(f"Raw query error: {e}")

def test_cursor():
    print("\n--- Testing Cursor ---")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM compiler_author LIMIT 2")
            rows = cursor.fetchall()
            print(f"Cursor result: {rows}")
    except Exception as e:
        print(f"Cursor error: {e}")

if __name__ == "__main__":
    test_aggregates()
    test_raw_query()
    test_cursor()
