"""
Dashboard Module for MOSDAC-Simplified
Handles user and admin dashboards
"""
import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from auth import get_db_connection
import time
import base64
from io import BytesIO
import json
from fpdf import FPDF
import tempfile
import os

# First, let's add the update_database_schema function
def update_database_schema():
    """Update database schema to include last_activity column if it doesn't exist"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if last_activity column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'last_activity' not in columns:
            # First add the column without a default value
            cursor.execute('''
                ALTER TABLE users 
                ADD COLUMN last_activity TIMESTAMP
            ''')
            
            # Then update all existing rows to set a default value
            cursor.execute('''
                UPDATE users 
                SET last_activity = created_at 
                WHERE last_activity IS NULL
            ''')
            
            # Finally, modify the column to have a default for new rows
            cursor.execute('''
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_admin BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    total_queries INTEGER DEFAULT 0,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Copy data to new table
            cursor.execute('''
                INSERT INTO users_new 
                SELECT 
                    id, username, email, password_hash, is_admin, 
                    created_at, last_login, is_active, total_queries,
                    COALESCE(last_activity, created_at) as last_activity
                FROM users
            ''')
            
            # Drop old table and rename new one
            cursor.execute('DROP TABLE users')
            cursor.execute('ALTER TABLE users_new RENAME TO users')
            
            # Recreate indexes and constraints
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users (username)
            ''')
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (email)
            ''')
            
            conn.commit()
            print("✅ Database schema updated: Added last_activity column to users table")
            
    except Exception as e:
        print(f"❌ Error updating database schema: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# Update the create_tables function to include last_activity
def create_tables():
    """Create database tables if they don't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Create users table with last_activity column
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
        total_queries INTEGER DEFAULT 0,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Rest of your table creation code...
    
    conn.commit()
    conn.close()
    update_database_schema()  # Ensure schema is updated after creating tables

# Update the log_chat function
def log_chat(user_id: int, query: str, response: str = None, response_time_ms: int = None) -> int:
    """Log chat history with optional response time and update query count.
    
    Args:
        user_id: The ID of the user sending the message
        query: The user's message/query
        response: The bot's response (optional)
        response_time_ms: Time taken to generate response in milliseconds (optional)
        
    Returns:
        int: The new total query count for the user
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, verify the user exists
        cursor.execute('SELECT id, COALESCE(total_queries, 0) FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        
        if user_data is None:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Get current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Log the chat
        cursor.execute(
            """INSERT INTO chat_history 
               (user_id, query, response, response_time_ms, timestamp) 
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, query, response, response_time_ms, current_time)
        )
        
        # Update user's query count and last_activity
        cursor.execute('''
            UPDATE users 
            SET total_queries = COALESCE(total_queries, 0) + 1,
                last_activity = ?
            WHERE id = ?
        ''', (current_time, user_id))
        
        # Get the updated count
        cursor.execute('SELECT COALESCE(total_queries, 0) FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        new_count = result[0] if result else 0
        
        # Commit the transaction
        conn.commit()
        return new_count
        
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"Error in log_chat: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        raise
    finally:
        if conn:
            conn.close()

# Update the get_user_analytics function
def get_user_analytics():
    """Get fresh analytics data for all users' queries"""
    conn = None
    try:
        conn = get_db_connection()
        conn.execute('PRAGMA read_uncommitted = 1')
        
        # Get user query statistics
        user_stats_query = '''
        SELECT 
            u.id as user_id,
            u.username,
            u.email,
            u.created_at,
            COALESCE(u.total_queries, 0) as total_queries,
            u.last_activity as last_query_time
        FROM users u
        ORDER BY COALESCE(u.total_queries, 0) DESC
        '''
        
        user_stats = pd.read_sql_query(user_stats_query, conn)
        
        # Get daily trends
        daily_trends_query = '''
        SELECT 
            DATE(timestamp) as query_date,
            COUNT(*) as query_count
        FROM chat_history
        WHERE timestamp >= date('now', '-30 days')
        GROUP BY DATE(timestamp)
        ORDER BY query_date
        '''
        daily_trends = pd.read_sql_query(daily_trends_query, conn)
        
        # Get top users
        top_users_query = '''
        SELECT 
            u.username,
            COUNT(*) as query_count
        FROM chat_history ch
        JOIN users u ON ch.user_id = u.id
        GROUP BY u.id, u.username
        ORDER BY query_count DESC
        LIMIT 10
        '''
        top_users = pd.read_sql_query(top_users_query, conn)
        
        return {
            'user_stats': user_stats,
            'daily_trends': daily_trends,
            'top_users': top_users
        }
        
    except Exception as e:
        st.error(f"Error fetching analytics: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None
    finally:
        if conn:
            conn.close()

def log_activity(user_id: int, activity_type: str, activity_data: str = None):
    """Log user activity to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_activity (user_id, activity_type, activity_data) VALUES (?, ?, ?)",
        (user_id, activity_type, activity_data)
    )
    conn.commit()
    conn.close()

def get_user_analytics():
    """Get fresh analytics data for all users' queries"""
    conn = None
    try:
        # Force a new connection to get fresh data
        conn = get_db_connection()
        
        # Ensure we're not using a cached connection
        conn.execute('PRAGMA read_uncommitted = 1')
        
        # Get user query statistics with the most recent data
        user_stats_query = '''
        SELECT 
            u.id as user_id,
            u.username,
            u.email,
            u.created_at,
            COALESCE(u.total_queries, 0) as total_queries,
            u.last_activity as last_query_time
        FROM users u
        ORDER BY COALESCE(u.total_queries, 0) DESC
        '''
        
        user_stats = pd.read_sql_query(user_stats_query, conn)
            
        # Get daily trends
        daily_trends_query = '''
        SELECT 
            DATE(timestamp) as query_date,
            COUNT(*) as query_count
        FROM chat_history
        WHERE timestamp >= date('now', '-30 days')
        GROUP BY DATE(timestamp)
        ORDER BY query_date
        '''
        daily_trends = pd.read_sql_query(daily_trends_query, conn)
        
        # Get top users
        top_users_query = '''
        SELECT 
            u.username,
            COUNT(*) as query_count
        FROM chat_history ch
        JOIN users u ON ch.user_id = u.id
        GROUP BY u.id, u.username
        ORDER BY query_count DESC
        LIMIT 10
        '''
        top_users = pd.read_sql_query(top_users_query, conn)
        
        return {
            'user_stats': user_stats,
            'daily_trends': daily_trends,
            'top_users': top_users
        }
        
    except Exception as e:
        st.error(f"Error fetching analytics: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None
    finally:
        if conn:
            conn.close()

def get_user_stats(user_id: int) -> dict:
    """Get user statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user info
    user = cursor.execute(
        "SELECT username, role, last_login FROM users WHERE id = ?", 
        (user_id,)
    ).fetchone()
    
    # Get query count
    query_count = cursor.execute(
        "SELECT COUNT(*) FROM chat_history WHERE user_id = ?", 
        (user_id,)
    ).fetchone()[0]
    
    # Get recent activities
    recent_activities = cursor.execute(
        "SELECT activity_type, activity_data, created_at "
        "FROM user_activity "
        "WHERE user_id = ? "
        "ORDER BY created_at DESC "
        "LIMIT 5",
        (user_id,)
    ).fetchall()
    
    conn.close()
    
    return {
        'username': user['username'],
        'query_count': query_count,
        'recent_activities': recent_activities
    }

def get_analytics_data():
    """Get analytics data for the admin dashboard"""
    conn = get_db_connection()
    
    # Get total users
    total_users = conn.execute('SELECT COUNT(DISTINCT id) FROM users').fetchone()[0]
    
    # Get total queries
    total_queries = conn.execute('SELECT COUNT(*) FROM chat_history').fetchone()[0]
    
    # Get average response time in seconds
    avg_response_time = conn.execute(
        'SELECT AVG(response_time_ms)/1000.0 FROM chat_history WHERE response_time_ms IS NOT NULL'
    ).fetchone()[0] or 0
    
    # Get user activity data
    user_activity = pd.read_sql(
        """
        SELECT 
            u.id as user_id,
            u.username,
            u.email,
            u.role,
            u.last_login,
            COUNT(ch.id) as total_queries,
            MAX(ch.timestamp) as last_active_date,
            AVG(ch.response_time_ms)/1000.0 as average_response_time
        FROM users u
        LEFT JOIN chat_history ch ON u.id = ch.user_id
        GROUP BY u.id, u.username, u.email, u.role, u.last_login
        ORDER BY total_queries DESC
        """,
        conn
    )
    
    # Convert timestamp to datetime
    if not user_activity.empty:
        user_activity['last_active_date'] = pd.to_datetime(user_activity['last_active_date'])
        user_activity['last_login'] = pd.to_datetime(user_activity['last_login'])
    
    conn.close()
    
    return {
        'total_users': total_users,
        'total_queries': total_queries,
        'avg_response_time': avg_response_time,
        'user_activity': user_activity
    }

def get_admin_stats():
    """Get admin dashboard statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get total users
    total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    
    # Get total questions
    total_questions = cursor.execute("SELECT COUNT(*) FROM chat_history").fetchone()[0]
    
    # Get user activity with more details
    user_activity = cursor.execute("""
        SELECT 
            u.id, 
            u.username, 
            u.email,
            u.role,
            u.created_at,
            u.last_login,
            COUNT(c.id) as query_count 
        FROM users u 
        LEFT JOIN chat_history c ON u.id = c.user_id 
        GROUP BY u.id, u.username, u.email, u.role, u.created_at, u.last_login
        ORDER BY u.created_at DESC
    """).fetchall()
    
    # Check if timestamp column exists in chat_history
    cursor.execute("PRAGMA table_info(chat_history)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Get recent chat history with more details
    if 'timestamp' in columns:
        recent_chats = cursor.execute("""
            SELECT 
                u.username, 
                u.role,
                c.query, 
                c.response, 
                c.timestamp,
                c.id as chat_id
            FROM chat_history c 
            JOIN users u ON c.user_id = u.id 
            ORDER BY c.timestamp DESC 
            LIMIT 20
        """).fetchall()
    else:
        # Fallback if timestamp column doesn't exist
        recent_chats = cursor.execute("""
            SELECT 
                u.username, 
                u.role,
                c.query, 
                c.response, 
                datetime('now') as timestamp,
                c.id as chat_id
            FROM chat_history c 
            JOIN users u ON c.user_id = u.id 
            ORDER BY c.id DESC 
            LIMIT 20
        """).fetchall()
    
    conn.close()
    
    return {
        'total_users': total_users,
        'total_questions': total_questions,
        'user_activity': user_activity,
        'recent_chats': recent_chats
    }

def get_table_download_link(df, filename, button_text):
    """Generates a link allowing the data in a given panda dataframe to be downloaded"""
    if df.empty:
        return ""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Analytics')
    b64 = base64.b64encode(output.getvalue()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">'
    href += f'<button style="background-color: #4CAF50; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">'
    href += f'{button_text}</button></a>'
    return href

def generate_pdf(df, title):
    """Generate PDF from dataframe"""
    pdf = FPDF()
    pdf.add_page()
    
    # Add title
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, title, 0, 1, 'C')
    pdf.ln(10)
    
    # Add date
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'R')
    pdf.ln(10)
    
    # Add metrics
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Summary Metrics', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    
    # Add table headers
    col_widths = [45, 45, 45, 45]
    headers = ['Total Users', 'Total Queries', 'Avg Response Time (s)', 'Timestamp']
    
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
    pdf.ln()
    
    # Add data row
    pdf.cell(col_widths[0], 10, str(df['user_id'].nunique()), 1, 0, 'C')
    pdf.cell(col_widths[1], 10, str(len(df)), 1, 0, 'C')
    pdf.cell(col_widths[2], 10, f"{df['average_response_time'].mean():.2f}" if not df.empty else 'N/A', 1, 0, 'C')
    pdf.cell(col_widths[3], 10, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1, 1, 'C')
    
    # Add detailed data
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Detailed User Activity', 0, 1, 'L')
    
    # Prepare data for table
    if not df.empty:
        # Convert datetime columns to string
        df_display = df.copy()
        for col in ['last_active_date', 'last_login']:
            if col in df_display.columns and pd.api.types.is_datetime64_any_dtype(df_display[col]):
                df_display[col] = df_display[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Format response time
        if 'average_response_time' in df_display.columns:
            df_display['average_response_time'] = df_display['average_response_time'].apply(
                lambda x: f"{x:.2f}s" if pd.notnull(x) else 'N/A'
            )
        
        # Add table headers
        headers = df_display.columns.tolist()
        col_width = 190 / len(headers)  # Distribute width evenly
        
        # Header
        pdf.set_font('Arial', 'B', 10)
        for header in headers:
            pdf.cell(col_width, 10, str(header), 1)
        pdf.ln()
        
        # Data
        pdf.set_font('Arial', '', 8)
        for _, row in df_display.iterrows():
            for header in headers:
                pdf.cell(col_width, 10, str(row[header]) if pd.notnull(row[header]) else '', 1)
            pdf.ln()
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf.output(temp_file.name)
    return temp_file.name

def show_user_dashboard(user_id: int):
    """Display user dashboard"""
    st.title("👤 User Dashboard")
    stats = get_user_stats(user_id)
    
    # User info card
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("👤 Username", stats['username'])
        st.metric("🔑 Role", stats['role'].capitalize())
    
    with col2:
        st.metric("❓ Total Queries", stats['query_count'])
        if stats['last_login']:
            st.metric("🕒 Last Login", stats['last_login'])
    
    # Recent activities
    st.subheader("📋 Recent Activities")
    if stats['recent_activities']:
        for activity in stats['recent_activities']:
            st.write(f"- **{activity['activity_type']}**: {activity['activity_data'] or ''} "
                   f"({activity['created_at']})")
    else:
        st.info("No recent activities found.")

def get_advanced_analytics():
    """Get comprehensive analytics data including response times, engagement, and patterns"""
    conn = None
    try:
        conn = get_db_connection()
        
        # Response Time Analytics
        response_time_query = '''
        SELECT 
            AVG(response_time_ms) as avg_response_time,
            MIN(response_time_ms) as min_response_time,
            MAX(response_time_ms) as max_response_time,
            COUNT(*) as total_queries_with_time
        FROM chat_history
        WHERE response_time_ms IS NOT NULL
        '''
        response_stats = pd.read_sql_query(response_time_query, conn)
        
        # Response time trends over time
        response_trends_query = '''
        SELECT 
            DATE(timestamp) as date,
            AVG(response_time_ms) as avg_response_time,
            COUNT(*) as query_count
        FROM chat_history
        WHERE response_time_ms IS NOT NULL
            AND timestamp >= date('now', '-30 days')
        GROUP BY DATE(timestamp)
        ORDER BY date
        '''
        response_trends = pd.read_sql_query(response_trends_query, conn)
        
        # User Engagement Metrics
        engagement_query = '''
        SELECT 
            COUNT(DISTINCT user_id) as total_users,
            COUNT(DISTINCT CASE WHEN timestamp >= date('now', '-7 days') THEN user_id END) as active_users_7d,
            COUNT(DISTINCT CASE WHEN timestamp >= date('now', '-30 days') THEN user_id END) as active_users_30d,
            COUNT(*) as total_queries
        FROM chat_history
        '''
        engagement_stats = pd.read_sql_query(engagement_query, conn)
        
        # Query Length Distribution
        query_length_query = '''
        SELECT 
            LENGTH(query) as query_length,
            COUNT(*) as count
        FROM chat_history
        GROUP BY LENGTH(query)
        ORDER BY query_length
        '''
        query_lengths = pd.read_sql_query(query_length_query, conn)
        
        # Peak Usage Times - Hourly
        hourly_usage_query = '''
        SELECT 
            CAST(strftime('%H', timestamp) AS INTEGER) as hour,
            COUNT(*) as query_count
        FROM chat_history
        WHERE timestamp >= date('now', '-30 days')
        GROUP BY hour
        ORDER BY hour
        '''
        hourly_usage = pd.read_sql_query(hourly_usage_query, conn)
        
        # Day of week usage
        daily_usage_query = '''
        SELECT 
            CASE CAST(strftime('%w', timestamp) AS INTEGER)
                WHEN 0 THEN 'Sunday'
                WHEN 1 THEN 'Monday'
                WHEN 2 THEN 'Tuesday'
                WHEN 3 THEN 'Wednesday'
                WHEN 4 THEN 'Thursday'
                WHEN 5 THEN 'Friday'
                WHEN 6 THEN 'Saturday'
            END as day_of_week,
            COUNT(*) as query_count
        FROM chat_history
        WHERE timestamp >= date('now', '-30 days')
        GROUP BY strftime('%w', timestamp)
        ORDER BY CAST(strftime('%w', timestamp) AS INTEGER)
        '''
        daily_usage = pd.read_sql_query(daily_usage_query, conn)
        
        # User Segmentation - New vs Returning
        user_segmentation_query = '''
        SELECT 
            u.id,
            u.username,
            u.created_at,
            COUNT(ch.id) as total_queries,
            MIN(ch.timestamp) as first_query,
            MAX(ch.timestamp) as last_query,
            CASE 
                WHEN julianday('now') - julianday(u.created_at) <= 7 THEN 'New'
                WHEN COUNT(ch.id) >= 10 THEN 'Power User'
                WHEN MAX(ch.timestamp) >= date('now', '-7 days') THEN 'Active'
                ELSE 'Inactive'
            END as user_segment
        FROM users u
        LEFT JOIN chat_history ch ON u.id = ch.user_id
        GROUP BY u.id, u.username, u.created_at
        '''
        user_segments = pd.read_sql_query(user_segmentation_query, conn)
        
        # User Growth Over Time
        user_growth_query = '''
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as new_users
        FROM users
        GROUP BY DATE(created_at)
        ORDER BY date
        '''
        user_growth = pd.read_sql_query(user_growth_query, conn)
        
        # Query Categories (based on length)
        query_categories = query_lengths.copy()
        if not query_categories.empty:
            query_categories['category'] = pd.cut(
                query_categories['query_length'],
                bins=[0, 50, 100, 200, float('inf')],
                labels=['Short (<50)', 'Medium (50-100)', 'Long (100-200)', 'Very Long (>200)']
            )
            query_categories = query_categories.groupby('category', observed=True)['count'].sum().reset_index()
        
        return {
            'response_stats': response_stats,
            'response_trends': response_trends,
            'engagement_stats': engagement_stats,
            'query_lengths': query_lengths,
            'query_categories': query_categories,
            'hourly_usage': hourly_usage,
            'daily_usage': daily_usage,
            'user_segments': user_segments,
            'user_growth': user_growth
        }
        
    except Exception as e:
        st.error(f"Error fetching advanced analytics: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None
    finally:
        if conn:
            conn.close()

def show_analytics_dashboard():
    """Display enhanced analytics dashboard with comprehensive metrics"""    
    
    # Clear any cached data
    if 'analytics_data' in st.session_state:
        del st.session_state.analytics_data
    
    # Show last update time
    current_time = pd.Timestamp.now()
    st.caption(f"Last updated: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Add refresh button
    if st.button("🔄 Refresh Data"):
        st.rerun()
    
    # Get fresh analytics data
    try:
        # Force a fresh data load
        analytics = get_user_analytics()
        advanced_analytics = get_advanced_analytics()
        
        if analytics is None or advanced_analytics is None:
            st.error("❌ Failed to load analytics data. Please try again.")
            return
        
        if not analytics or 'user_stats' not in analytics or analytics['user_stats'].empty:
            st.info("ℹ️ No query data available yet. Start chatting to see analytics.")
            return
            
        user_stats = analytics['user_stats']
        daily_trends = analytics.get('daily_trends', pd.DataFrame())
        
        # ===== KEY METRICS SECTION =====
        st.header("📈 Key Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_users = len(user_stats)
            st.metric("👥 Total Users", total_users)
        
        with col2:
            total_queries = user_stats['total_queries'].sum()
            st.metric("💬 Total Queries", total_queries)
        
        with col3:
            if not advanced_analytics['response_stats'].empty:
                avg_response = advanced_analytics['response_stats']['avg_response_time'].iloc[0]
                st.metric("⚡ Avg Response Time", f"{avg_response:.0f} ms" if pd.notnull(avg_response) else "N/A")
            else:
                st.metric("⚡ Avg Response Time", "N/A")
        
        st.markdown("---")
        
        # ===== USER TABLE SECTION =====
        st.header("👥 User Statistics Table")
        if not user_stats.empty:
            # Get additional user info from database
            conn = get_db_connection()
            try:
                user_details_query = '''
                SELECT 
                    u.id,
                    u.username,
                    u.email,
                    u.last_login,
                    COALESCE(u.total_queries, 0) as total_queries,
                    u.last_activity
                FROM users u
                ORDER BY COALESCE(u.total_queries, 0) DESC
                '''
                user_details = pd.read_sql_query(user_details_query, conn)
                
                if not user_details.empty:
                    # Format the display dataframe
                    display_df = user_details[['username', 'email', 'last_login', 'total_queries', 'last_activity']].copy()
                    display_df.columns = ['Username', 'Email', 'Last Login', 'Total Queries', 'Last Activity']
                    
                    # Format datetime columns
                    for col in ['Last Login', 'Last Activity']:
                        if col in display_df.columns:
                            display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%Y-%m-%d %H:%M')
                    
                    # Display the table with enhanced styling
                    st.dataframe(
                        display_df,
                        column_config={
                            "Username": st.column_config.TextColumn(
                                "Username",
                                help="User's username",
                                width="medium"
                            ),
                            "Email": st.column_config.TextColumn(
                                "Email",
                                help="User's email address",
                                width="large"
                            ),
                            "Last Login": st.column_config.TextColumn(
                                "Last Login",
                                help="Last login timestamp",
                                width="medium"
                            ),
                            "Total Queries": st.column_config.NumberColumn(
                                "Total Queries",
                                help="Number of queries asked by the user",
                                format="%d",
                                width="small"
                            ),
                            "Last Activity": st.column_config.TextColumn(
                                "Last Activity",
                                help="Last activity timestamp",
                                width="medium"
                            )
                        },
                        use_container_width=True,
                        hide_index=True,
                        height=400
                    )
                    
                else:
                    st.info("No user data available.")
            finally:
                conn.close()
        else:
            st.info("No user statistics available.")
        
        st.markdown("---")
                
        # ===== QUERY ANALYTICS SECTION =====
        st.header("💬 Query Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Query Length Distribution
            st.subheader("Query Complexity")
            if not advanced_analytics['query_categories'].empty:
                fig_categories = px.bar(
                    advanced_analytics['query_categories'],
                    x='category',
                    y='count',
                    title='Query Distribution by Length',
                    labels={'category': 'Query Length', 'count': 'Number of Queries'},
                    color='count',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig_categories, use_container_width=True)
            else:
                st.info("No query length data available.")
        
        with col2:
            # Top Active Users
            st.subheader("🏆 Top Active Users")
            if 'top_users' in analytics and not analytics['top_users'].empty:
                top_users = analytics['top_users'].head(10)
                
                fig_top = px.bar(
                    top_users,
                    x='query_count',
                    y='username',
                    orientation='h',
                    title='Top 10 Users by Query Count',
                    labels={'username': 'Username', 'query_count': 'Queries'},
                    color='query_count',
                    color_continuous_scale='Blues'
                )
                fig_top.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_top, use_container_width=True)
            else:
                st.info("No top users data available.")        
        
        # ===== PERFORMANCE METRICS SECTION =====
        st.header("⚡ Performance Metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Response Time Statistics
            st.subheader("Response Time Stats")
            if not advanced_analytics['response_stats'].empty:
                resp_stats = advanced_analytics['response_stats'].iloc[0]
                
                perf_data = pd.DataFrame({
                    'Metric': ['Average', 'Minimum', 'Maximum'],
                    'Time (ms)': [
                        resp_stats['avg_response_time'] if pd.notnull(resp_stats['avg_response_time']) else 0,
                        resp_stats['min_response_time'] if pd.notnull(resp_stats['min_response_time']) else 0,
                        resp_stats['max_response_time'] if pd.notnull(resp_stats['max_response_time']) else 0
                    ]
                })
                
                fig_perf = px.bar(
                    perf_data,
                    x='Metric',
                    y='Time (ms)',
                    title='Response Time Statistics',
                    color='Time (ms)',
                    color_continuous_scale='RdYlGn_r'
                )
                st.plotly_chart(fig_perf, use_container_width=True)
            else:
                st.info("No response time data available.")
        
        st.markdown("---")
        
        # ===== EXPORT COMPLETE STATISTICS =====        
        try:
            # Get user details again for export
            conn = get_db_connection()
            user_details_query = '''
            SELECT 
                u.id,
                u.username,
                u.email,
                u.last_login,
                COALESCE(u.total_queries, 0) as total_queries,
                u.last_activity,
                u.created_at
            FROM users u
            ORDER BY COALESCE(u.total_queries, 0) DESC
            '''
            complete_user_data = pd.read_sql_query(user_details_query, conn)
            
            # Get query history summary
            query_summary = '''
            SELECT 
                u.username,
                COUNT(ch.id) as query_count,
                AVG(ch.response_time_ms) as avg_response_time,
                MIN(ch.timestamp) as first_query,
                MAX(ch.timestamp) as last_query
            FROM users u
            LEFT JOIN chat_history ch ON u.id = ch.user_id
            GROUP BY u.id, u.username
            ORDER BY query_count DESC
            '''
            query_data = pd.read_sql_query(query_summary, conn)
            conn.close()
            
            # Create Excel file with multiple sheets
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Sheet 1: User Statistics
                complete_user_data.to_excel(writer, sheet_name='User Statistics', index=False)
                
                # Sheet 2: Query Summary
                query_data.to_excel(writer, sheet_name='Query Summary', index=False)
                
                # Sheet 3: Daily Trends
                if not daily_trends.empty:
                    daily_trends.to_excel(writer, sheet_name='Daily Trends', index=False)
                
                # Sheet 4: User Segments
                if not advanced_analytics['user_segments'].empty:
                    advanced_analytics['user_segments'].to_excel(writer, sheet_name='User Segments', index=False)
                
                # Sheet 5: Response Time Stats
                if not advanced_analytics['response_stats'].empty:
                    advanced_analytics['response_stats'].to_excel(writer, sheet_name='Response Times', index=False)
                
                # Sheet 6: Hourly Usage
                if not advanced_analytics['hourly_usage'].empty:
                    advanced_analytics['hourly_usage'].to_excel(writer, sheet_name='Hourly Usage', index=False)
                
                # Sheet 7: Daily Usage
                if not advanced_analytics['daily_usage'].empty:
                    advanced_analytics['daily_usage'].to_excel(writer, sheet_name='Weekly Pattern', index=False)
            
            excel_data = output.getvalue()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="📄 Download User Stats",
                    data=excel_data,
                    file_name=f"complete_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )
            
        except Exception as export_error:
            st.error(f"Error preparing export: {str(export_error)}")
        
    except Exception as e:
        st.error(f"❌ Error loading analytics: {str(e)}")
        import traceback
        st.error(traceback.format_exc())


def show_admin_dashboard():
    """Display admin dashboard with analytics and user activity"""
    st.title("📊 Analytics Dashboard")
    
    # Get analytics data
    data = get_analytics_data()
    
    # Display metrics in columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Total Users", data['total_users'])
    with col2:
        st.metric("💬 Total Queries", data['total_queries'])
    with col3:
        st.metric("⏱️ Avg Response Time", f"{data['avg_response_time']:.2f} seconds" if data['avg_response_time'] else "N/A")
    
    st.markdown("---")
    
    # User Activity Table
    st.subheader("User Activity")
    
    # Add search and filter options
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("Search by username or email", "")
    with col2:
        min_queries = st.number_input("Minimum queries", min_value=0, value=0)
    
    # Apply filters
    filtered_data = data['user_activity'].copy()
    if search_term:
        mask = (filtered_data['username'].str.contains(search_term, case=False, na=False)) | \
               (filtered_data['email'].str.contains(search_term, case=False, na=False))
        filtered_data = filtered_data[mask]
    
    if min_queries > 0:
        filtered_data = filtered_data[filtered_data['total_queries'] >= min_queries]
    
    # Display the table
    if not filtered_data.empty:
        # Format the DataFrame for display
        display_columns = {
            'username': 'Username',
            'email': 'Email',
            'total_queries': 'Total Queries',
            'last_active_date': 'Last Active',
            'average_response_time': 'Avg Response Time (s)',
            'role': 'Role',
            'last_login': 'Last Login'
        }
        
        # Format the data for display
        display_df = filtered_data[list(display_columns.keys())].copy()
        display_df = display_df.rename(columns=display_columns)
        
        # Format datetime columns
        for col in ['Last Active', 'Last Login']:
            if col in display_df.columns:
                display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M')
        
        # Format response time
        if 'Avg Response Time (s)' in display_df.columns:
            display_df['Avg Response Time (s)'] = display_df['Avg Response Time (s)'].apply(
                lambda x: f"{x:.2f}" if pd.notnull(x) else 'N/A'
            )
        
        # Display the user activity table with sortable columns
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Username': 'Username',
                'Email': 'Email',
                'Role': st.column_config.SelectboxColumn(
                    'Role',
                    help="User role",
                    options=["admin", "user"],
                    required=True
                ),
                'Query Count': st.column_config.NumberColumn(
                    'Queries',
                    help="Number of queries made by the user"
                ),
                'Last Active': 'Last Active'
            },
            height=400
        )
        
        # Add expandable sections for detailed user activity
        st.subheader("📋 User Details")
        selected_user = st.selectbox(
            "Select a user to view details",
            [""] + display_df['Username'].tolist() if not display_df.empty else [""],
            format_func=lambda x: "Select a user..." if x == "" else x
        )
        
        if selected_user:
            user_row = display_df[display_df['Username'] == selected_user].iloc[0]
            user_id_query = data['user_activity'][data['user_activity']['username'] == selected_user]['user_id'].values[0]
            with st.expander(f"👤 {selected_user}'s Activity", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Queries", user_row['Total Queries'])
                with col2:
                    st.metric("Role", user_row['Role'])
                with col3:
                    st.metric("Last Login", user_row['Last Login'])
                # FULL Query history
                st.subheader("Full Query History")
                conn = get_db_connection()
                try:
                    user_query_df = pd.read_sql_query(
                        "SELECT query AS Query, response AS Response, timestamp AS Time FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC",
                        conn,
                        params=(user_id_query,)
                    )
                    if not user_query_df.empty:
                        st.dataframe(user_query_df, use_container_width=True, hide_index=True)
                        csv = user_query_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="💾 Download User's Queries as CSV",
                            data=csv,
                            file_name=f"{selected_user}_queries.csv",
                            mime='text/csv',
                        )
                    else:
                        st.info("No queries found for this user.")
                finally:
                    conn.close()
                # Login history
                st.subheader("Login History")
                conn = get_db_connection()
                try:
                    login_history = pd.read_sql_query(
                        "SELECT last_login FROM users WHERE id = ?",
                        conn,
                        params=(user_id_query,)
                    )
                    if not login_history.empty:
                        st.dataframe(login_history, use_container_width=True, hide_index=True)
                    else:
                        st.info("No login history found for this user.")
                finally:
                    conn.close()
                st.write(f"**Last Activity:** {user_row['Last Active']}")
        
        # Query Analytics Section
        st.markdown("---")
        st.subheader("📊 Query Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Query Distribution by User (Bar Chart)
            st.markdown("**Queries by User**")
            if not display_df.empty and 'Username' in display_df.columns and 'Query Count' in display_df.columns:
                # Sort by query count and get top 10
                top_users = display_df.sort_values('Query Count', ascending=False).head(10).copy()
                fig1 = px.bar(
                    top_users, 
                    x='Username', 
                    y='Query Count',
                    color='Query Count',
                    color_continuous_scale='Blues',
                    labels={'Query Count': 'Number of Queries', 'Username': 'User'}
                )
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("No user query data available.")
        
        with col2:
            # Query Distribution by Role (Pie Chart)
            st.markdown("**Queries by Role**")
            if not display_df.empty and 'Role' in display_df.columns and 'Query Count' in display_df.columns:
                role_counts = display_df.groupby('Role')['Query Count'].sum().reset_index()
                fig2 = px.pie(
                    role_counts,
                    values='Query Count',
                    names='Role',
                    hole=0.3,
                    color_discrete_sequence=px.colors.sequential.Blues_r
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No role-based query data available.")
        
        # Query Trends Over Time (Line Chart)
        st.markdown("**Query Trends Over Time**")
        try:
            # Get query data for the last 30 days
            conn = get_db_connection()
            query = """
                SELECT date(timestamp) as date, COUNT(*) as count
                FROM chat_history
                WHERE timestamp >= date('now', '-30 days')
                GROUP BY date(timestamp)
                ORDER BY date
            """
            trends_df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not trends_df.empty:
                fig3 = px.line(
                    trends_df,
                    x='date',
                    y='count',
                    markers=True,
                    labels={'date': 'Date', 'count': 'Number of Queries'},
                    title='Daily Query Volume (Last 30 Days)'
                )
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No query data available for the last 30 days.")
                
        except Exception as e:
            st.error(f"Error loading query trends: {str(e)}")
    else:
        st.info("No user activity data available.")
        
        # Format dates
        users_df['Joined'] = pd.to_datetime(users_df['Joined']).dt.strftime('%Y-%m-%d %H:%M')
        users_df['Last Login'] = pd.to_datetime(users_df['Last Login']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Display user table with more details
        st.dataframe(
            users_df,
            column_config={
                'ID': 'ID',
                'Username': 'Username',
                'Email': 'Email',
                'Role': 'Role',
                'Joined': 'Joined',
                'Last Login': 'Last Login',
                'Query Count': 'Queries'
            },
            hide_index=True,
            use_container_width=True
        )
        
        # User activity chart
        st.subheader("📊 User Activity")
        fig = px.bar(users_df, x='Username', y='Query Count', 
                     title='Queries per User',
                     color='Query Count',
                     color_continuous_scale='Blues')
        st.plotly_chart(fig, use_container_width=True)
    
    # Chat history section with search and filter
    st.subheader("💬 Chat History")
    if data.get('recent_chats'):
        chat_df = pd.DataFrame(data['recent_chats'], 
                             columns=['User', 'Role', 'Query', 'Response', 'Timestamp', 'ID'])
        
        # Add search and filter
        search_col, filter_col = st.columns([3, 1])
        with search_col:
            search_query = st.text_input("Search chats", "", 
                                       placeholder="Search by user or query...")
        with filter_col:
            role_filter = st.selectbox("Role", ["All"] + sorted(chat_df['Role'].unique().tolist()))
        
        # Apply filters
        if search_query:
            search_query = search_query.lower()
            chat_df = chat_df[
                chat_df['User'].str.lower().str.contains(search_query) |
                chat_df['Query'].str.lower().str.contains(search_query) |
                chat_df['Response'].str.lower().str.contains(search_query)
            ]
        
        if role_filter != "All":
            chat_df = chat_df[chat_df['Role'] == role_filter]
        
        # Display the filtered chat history
        st.dataframe(
            chat_df[['User', 'Role', 'Query', 'Timestamp']].sort_values('Timestamp', ascending=False),
            column_config={
                'User': 'User',
                'Role': 'Role',
                'Query': 'Query',
                'Timestamp': 'Time'
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No chat history found.")
        
    # Add some admin actions
    st.subheader("⚙️ Admin Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    with col2:
        if st.button("📊 Export Data"):
            # Create a CSV file in memory
            csv = chat_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="💾 Download Chat History",
                data=csv,
                file_name=f"chat_history_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime='text/csv',
            )

update_database_schema()

