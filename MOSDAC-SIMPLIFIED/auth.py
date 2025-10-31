"""
Authentication Module for MOSDAC-Simplified
Handles user registration, login, and database operations
"""

import sqlite3
import hashlib
import re
from pathlib import Path

# Database configuration
DB_NAME = "users.db"

def get_db_connection():
    """
    Create and return a database connection
    Returns:
        sqlite3.Connection: Database connection object
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def migrate_database():
    """
    Run database migrations to update schema if needed
    """
    print("Starting database migration...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Disable foreign key constraints during migration
        cursor.execute('PRAGMA foreign_keys = OFF')
        
        # Check if chat_history table exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_history'")
        if cursor.fetchone():
            # Check if timestamp column exists in chat_history
            cursor.execute("PRAGMA table_info(chat_history)")
            columns = [column[1].lower() for column in cursor.fetchall()]
            
            # Add timestamp column to chat_history if it doesn't exist
            if 'timestamp' not in columns:
                print("Migrating chat_history table to add timestamp column...")
                # Create a temporary table with the new schema
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chat_history_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        query TEXT NOT NULL,
                        response TEXT,
                        response_time_ms INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # Copy data from old table to new table
                cursor.execute('''
                    INSERT INTO chat_history_new (id, user_id, query, response, response_time_ms, timestamp)
                    SELECT id, user_id, query, response, response_time_ms, datetime('now') 
                    FROM chat_history
                ''')
                
                # Drop the old table
                cursor.execute('DROP TABLE IF EXISTS chat_history')
                
                # Rename the new table
                cursor.execute('ALTER TABLE chat_history_new RENAME TO chat_history')
                
                # Recreate indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_history_timestamp ON chat_history(timestamp)')
                
                print("Successfully added timestamp column to chat_history table")
        
        # Check if user_activity table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_activity'")
        if cursor.fetchone():
            # Check if timestamp column exists in user_activity
            cursor.execute("PRAGMA table_info(user_activity)")
            columns = [column[1].lower() for column in cursor.fetchall()]
            
            # Add timestamp column to user_activity if it doesn't exist
            if 'timestamp' not in columns:
                print("Migrating user_activity table to add timestamp column...")
                # Create a temporary table with the new schema
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_activity_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        activity_type TEXT NOT NULL,
                        activity_data TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')
                
                # Copy data from old table to new table
                cursor.execute('''
                    INSERT INTO user_activity_new (id, user_id, activity_type, activity_data, timestamp)
                    SELECT id, user_id, activity_type, activity_data, datetime('now') 
                    FROM user_activity
                ''')
                
                # Drop the old table
                cursor.execute('DROP TABLE IF EXISTS user_activity')
                
                # Rename the new table
                cursor.execute('ALTER TABLE user_activity_new RENAME TO user_activity')
                
                # Recreate indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_activity_timestamp ON user_activity(timestamp)')
                
                print("Successfully added timestamp column to user_activity table")
        
        conn.commit()
        print("Database migration completed successfully")
            
    except Exception as e:
        print(f"Error during database migration: {e}")
        conn.rollback()
        raise
    finally:
        # Re-enable foreign key constraints
        cursor.execute('PRAGMA foreign_keys = ON')
        conn.close()


def init_database():
    """
    Initialize the database and create tables if they don't exist
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Disable foreign key constraints temporarily to avoid issues with table recreation
        cursor.execute('PRAGMA foreign_keys = OFF')
        
        try:
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                total_queries INTEGER DEFAULT 0
            )
            ''')
            
            # Create user_activity table with timestamp column
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                activity_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            ''')
            
            # Create chat_history table with timestamp column
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                query TEXT NOT NULL,
                response TEXT,
                response_time_ms INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            ''')
            
            # Create user_queries table for analytics
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                query_count INTEGER DEFAULT 1,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_history_timestamp ON chat_history(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_activity_timestamp ON user_activity(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_queries_user_id ON user_queries(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_queries_username ON user_queries(username)')
            
            # Always delete and recreate admin user to ensure credentials are reset
            admin_username = "admin"
            admin_email = "admin@example.com"
            admin_password = "admin123"  # In production, use a secure password
            
            # Delete existing admin user if exists
            cursor.execute('DELETE FROM users WHERE username = ?', (admin_username,))
            
            # Create admin user with hashed password
            password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
            cursor.execute(
                'INSERT INTO users (username, email, password_hash, is_admin, is_active) VALUES (?, ?, ?, ?, ?)',
                (admin_username, admin_email, password_hash, 1, 1)
            )
            print(f"[SUCCESS] Created admin user with username: {admin_username}, password: {admin_password}")
            
            # Always delete and recreate bhumi user to ensure credentials are reset
            bhumi_username = "bhumi"
            bhumi_email = "bhumi@example.com"
            bhumi_password = "Bhumi@23"  # Using the password from run.bat
            
            # Delete existing bhumi user if exists
            cursor.execute('DELETE FROM users WHERE username = ?', (bhumi_username,))
            
            # Create bhumi user with hashed password
            password_hash = hashlib.sha256(bhumi_password.encode()).hexdigest()
            cursor.execute(
                'INSERT INTO users (username, email, password_hash, is_admin, is_active) VALUES (?, ?, ?, ?, ?)',
                (bhumi_username, bhumi_email, password_hash, 1, 1)
            )
            print(f"[SUCCESS] Created bhumi user with username: {bhumi_username}, password: {bhumi_password}")
            
            # Re-enable foreign key constraints
            cursor.execute('PRAGMA foreign_keys = ON')
            
            # Commit all changes
            conn.commit()
            
        except Exception as e:
            print(f"Error during database initialization: {e}")
            if conn:
                conn.rollback()
            raise
            
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        raise
        
    finally:
        if conn:
            conn.close()


def hash_password(password):
    """
    Hash a password using SHA-256
    Args:
        password (str): Plain text password
    Returns:
        str: Hashed password
    """
    return hashlib.sha256(password.encode()).hexdigest()


def validate_email(email):
    """
    Validate email format using regex
    Args:
        email (str): Email address to validate
    Returns:
        bool: True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username):
    """
    Validate username (alphanumeric, 3-20 characters)
    Args:
        username (str): Username to validate
    Returns:
        bool: True if valid, False otherwise
    """
    return len(username) >= 3 and len(username) <= 20 and username.isalnum()


def validate_password(password):
    """
    Validate password strength (minimum 6 characters)
    Args:
        password (str): Password to validate
    Returns:
        bool: True if valid, False otherwise
    """
    return len(password) >= 6


def register_user(username, email, password, is_admin=False):
    """
    Register a new user in the database
    Args:
        username (str): Unique username
        email (str): Unique email address
        password (str): Plain text password (will be hashed)
        is_admin (bool): Whether the user should be an admin
    Returns:
        tuple: (success: bool, message: str)
    """
    # Input validation
    if not all([username, email, password]):
        return False, "All fields are required"
    
    if not validate_email(email):
        return False, "Invalid email format"
        
    if not validate_username(username):
        return False, "Username must be 3-20 characters long and alphanumeric"
        
    if not validate_password(password):
        return False, "Password must be at least 6 characters long"
    
    # Hash the password
    hashed_password = hash_password(password)
    
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if username or email already exists
        cursor.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        )
        if cursor.fetchone() is not None:
            return False, "Username or email already exists"
        
        # Set role
        role = 'admin' if is_admin else 'user'
        
        # Insert new user
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
            (username, email, hashed_password, is_admin)
        )
        
        # Log the registration
        user_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO user_activity (user_id, activity_type, activity_data) VALUES (?, ?, ?)",
            (user_id, 'user_registered', f'New {role} account created')
        )
        
        conn.commit()
        return True, f"{role.capitalize()} registration successful!"
        conn.close()
        return True, "Registration successful! Please login."
        
    except sqlite3.IntegrityError as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"An error occurred: {str(e)}"


def authenticate_user(username, password):
    """
    Authenticate a user by username and password
    Args:
        username (str): Username
        password (str): Plain text password
    Returns:
        tuple: (success: bool, message: str, user_data: dict or None)
    """
    if not username or not password:
        return False, "Username and password are required", None
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get user by username
        cursor.execute(
            "SELECT id, username, email, password_hash, is_admin FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
        
        if user is None:
            return False, "Invalid username or password", None
            
        # Verify password
        hashed_password = hash_password(password)
        if user['password_hash'] != hashed_password:
            return False, "Invalid username or password", None
            
        # Update last login time
        cursor.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user['id'],)
        )
        
        # Log the login activity
        cursor.execute(
            "INSERT INTO user_activity (user_id, activity_type) VALUES (?, ?)",
            (user['id'], 'user_login')
        )
        
        conn.commit()
        
        # Return user data
        return True, "Login successful", {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'is_admin': bool(user['is_admin'])
        }
        
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}", None
        
    finally:
        conn.close()


def get_user_by_id(user_id):
    """
    Retrieve user information by user ID
    Args:
        user_id (int): User ID
    Returns:
        dict or None: User data if found, None otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, email FROM users WHERE id = ?",
            (user_id,)
        )
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"]
            }
        return None
        
    except Exception as e:
        print(f"Error fetching user: {str(e)}")
        return None


    # Initialize database when module is imported
init_database()
# Run migrations to ensure schema is up-to-date
migrate_database()
