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

def log_chat(user_id: int, query: str, response: str, response_time_ms: int = None):
    """Log chat history with optional response time"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO chat_history 
           (user_id, query, response, response_time_ms) 
           VALUES (?, ?, ?, ?)""",
        (user_id, query, response, response_time_ms)
    )
    conn.commit()
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
            user_data = users_df[users_df['Username'] == selected_user].iloc[0]
            
            with st.expander(f"👤 {selected_user}'s Activity", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Queries", user_data['Query Count'])
                with col2:
                    st.metric("Role", user_data['Role'])
                with col3:
                    st.metric("Member Since", user_data['Joined'])
                
                # Show recent queries
                st.subheader("Recent Queries")
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT query, response, timestamp 
                        FROM chat_history 
                        WHERE user_id = ? 
                        ORDER BY timestamp DESC 
                        LIMIT 10
                    """, (user_data['ID'],))
                    recent_queries = cursor.fetchall()
                    
                    if recent_queries:
                        for i, (query, response, timestamp) in enumerate(recent_queries, 1):
                            with st.container():
                                st.markdown(f"**{i}. {timestamp}**")
                                st.markdown(f"**Q:** {query}")
                                st.markdown(f"**A:** {response}")
                                st.markdown("---")
                    else:
                        st.info("No recent queries from this user.")
                finally:
                    conn.close()
        
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
    if stats['recent_chats']:
        chat_df = pd.DataFrame(stats['recent_chats'], 
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
