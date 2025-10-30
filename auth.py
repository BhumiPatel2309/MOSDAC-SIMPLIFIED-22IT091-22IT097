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
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if timestamp column exists in chat_history
        cursor.execute("PRAGMA table_info(chat_history)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add timestamp column if it doesn't exist
        if 'timestamp' not in columns:
            cursor.execute("""
                ALTER TABLE chat_history 
                ADD COLUMN timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            conn.commit()
            
            # Update existing records with current timestamp
            cursor.execute("""
                UPDATE chat_history 
                SET timestamp = datetime('now') 
                WHERE timestamp IS NULL
            """)
            conn.commit()
            
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()


def init_database():
    """
    Initialize the database and create tables if they don't exist
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table with proper constraints
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create user_activity table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            activity_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # Create chat_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            query TEXT NOT NULL,
            response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()
    
    # Run migrations
    migrate_database()


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
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (username, email, hashed_password, role)
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
            "SELECT id, username, email, password, role FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
        
        if user is None:
            return False, "Invalid username or password", None
            
        # Verify password
        hashed_password = hash_password(password)
        if user['password'] != hashed_password:
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
        
        # Return user data (without password)
        user_data = {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role']
        }
        
        return True, "Login successful", user_data
        
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
