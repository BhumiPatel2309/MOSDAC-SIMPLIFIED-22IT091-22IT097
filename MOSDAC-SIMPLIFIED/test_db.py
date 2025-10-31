import sqlite3
import os
from auth import init_database, get_db_connection

# Delete existing database if it exists
if os.path.exists('users.db'):
    os.remove('users.db')

print("Initializing database...")
init_database()

# Verify the database was created and has the correct tables
conn = get_db_connection()
try:
    cursor = conn.cursor()
    
    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print("\nTables in database:", tables)
    
    # Check users table structure
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [row[1] for row in cursor.fetchall()]
    print("\nUsers table columns:", user_columns)
    
    # Check if admin user exists
    cursor.execute("SELECT username, is_admin FROM users WHERE username IN ('admin', 'bhumi')")
    users = cursor.fetchall()
    print("\nUsers:")
    for user in users:
        print(f"- {user[0]} (admin: {bool(user[1])})")
    
    # Check indexes
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
    print("\nIndexes:")
    for idx in cursor.fetchall():
        print(f"- {idx[0]}")
    
    print("\nDatabase initialization successful!")
    
except Exception as e:
    print(f"Error verifying database: {e}")
    raise
finally:
    conn.close()
