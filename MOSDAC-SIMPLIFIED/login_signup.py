import streamlit as st
from auth import register_user, authenticate_user


def apply_auth_styles():
    """
    Apply custom CSS styles for authentication pages with dark theme
    """
    st.markdown("""
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Dark Theme Variables */
        :root {
            --primary: #7c4dff;
            --primary-dark: #651fff;
            --secondary: #1e1e2d;
            --dark: #121212;
            --darker: #0a0a0a;
            --light: #e0e0e0;
            --text: #ffffff;
            --text-secondary: #b0b0b0;
        }
        
        /* Base Styles */
        .stApp {
            background: var(--darker) !important;
            color: var(--text) !important;
        }
        
        .main {
            font-family: 'Inter', sans-serif;
            background: var(--darker) !important;
            color: var(--text) !important;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        /* Auth Container */
        .auth-container {
            max-width: 700px;
            width: 95%;
            margin: 2rem auto;
            padding: 2.5rem 3rem;
            background: var(--secondary);
            border-radius: 24px;
            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        /* Auth Header */
        .auth-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .auth-header h1 {
            color: var(--primary);
            font-size: 2.75rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
            letter-spacing: -0.5px;
        }
        
        .auth-header p {
            color: var(--text-secondary);
            font-size: 1.1rem;
            font-weight: 400;
            line-height: 1.6;
            margin-bottom: 2rem !important;
        }
        
        /* Input Fields */
        .stTextInput > div > div > input {
            border-radius: 14px;
            border: 2px solid rgba(255, 255, 255, 0.1);
            background-color: var(--dark) !important;
            color: var(--text) !important;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            transition: all 0.3s ease;
            height: auto;
            min-height: 48px;
            margin-bottom: 1rem;
        }

        .stTextInput > div > div > input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 4px rgba(124, 77, 255, 0.2);
            transform: translateY(-1px);
        }
        
        .stTextInput > div > div > input:hover {
            border-color: rgba(255, 255, 255, 0.2);
        }
        
        .stTextInput > label {
            font-size: 1.05rem !important;
            font-weight: 500 !important;
            margin-bottom: 0.5rem !important;
            color: var(--text) !important;
        }
        
        /* Buttons */
        .stButton > button {
            width: 100%;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 14px;
            padding: 1rem 2rem !important;
            font-size: 1.1rem !important;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease !important;
            height: auto !important;
            min-height: 56px;
            margin-top: 0.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 15px rgba(124, 77, 255, 0.3);
        }
        
        .stButton > button:hover {
            transform: translateY(-3px) scale(1.01);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.3) !important;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
        }
        
        .stButton > button:active {
            transform: translateY(0) scale(0.99);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2) !important;
        }
        
        /* Success/Error Messages */
        .stSuccess, .stError, .stWarning, .stInfo {
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            background-color: rgba(0, 0, 0, 0.2) !important;
        }
        
        /* Link Styles */
        .auth-link {
            text-align: center;
            margin: 2rem 0 1.5rem;
            color: var(--text-secondary);
            font-size: 1.05rem;
            line-height: 1.6;
        }
        
        .auth-link a {
            color: var(--primary) !important;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        
        .auth-link a:hover {
            color: var(--primary-dark) !important;
            text-decoration: underline;
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Divider */
        .divider {
            text-align: center;
            margin: 1rem 0;
            color: var(--text-secondary);
            font-size: 0.95rem;
        }
    </style>
    """, unsafe_allow_html=True)


def show_signup_page():
    """
    Display the signup page with form validation
    Allows new users to register with username, email, and password
    """
    apply_auth_styles()
    
    # Center the form with full width
    col1, col2, col3 = st.columns([0.5, 9, 0.5])
    
    with col2:
        # Header with improved spacing
        st.markdown("""
        <div class="auth-header">
            <h1>Create Account</h1>
            <p>Join us today to access all features</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Signup form with single column layout
        with st.form("signup_form", clear_on_submit=True):
            username = st.text_input(
                "Username",
                placeholder="Enter username (3-20 characters)",
                help="Alphanumeric characters only"
            )
            
            email = st.text_input(
                "Email Address",
                placeholder="Enter your email",
                help="We'll never share your email with anyone else"
            )
            
            password = st.text_input(
                "Create Password",
                type="password",
                placeholder="Enter a strong password",
                help="Minimum 8 characters with numbers and special characters"
            )
            
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Re-enter your password"
            )
            
            submit_button = st.form_submit_button(
                "Create Account",
                type="primary",
                use_container_width=True
            )
            
            if submit_button:
                # Validation with better error messages
                if not username or not email or not password or not confirm_password:
                    st.error("⚠️ Please fill in all required fields")
                elif len(password) < 8:
                    st.error("🔒 Password must be at least 8 characters long")
                elif password != confirm_password:
                    st.error("🔒 Passwords do not match. Please try again.")
                else:
                    # Show loading state
                    with st.spinner("Creating your account..."):
                        # Attempt registration
                        success, message = register_user(username, email, password)
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.balloons()
                            st.session_state.show_login = True
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
        
        # Divider with text and login link
        st.markdown("""
        <div style="display: flex; align-items: center; margin: 2rem 0; color: var(--text-secondary);">
            <div style="flex-grow: 1; height: 1px; background: rgba(255, 255, 255, 0.1);"></div>
            <span style="padding: 0 1rem; font-size: 0.9rem; color: rgba(255, 255, 255, 0.5);">or</span>
            <div style="flex-grow: 1; height: 1px; background: rgba(255, 255, 255, 0.1);"></div>
        </div>
        <div style="text-align: center; margin: 1.25rem 0;">
            Already have an account? <a href="#" style="color: var(--primary); text-decoration: none; font-weight: 500;" onclick="window.parent.document.querySelector('button[data-testid=\"baseButton-secondary\"]').click();">Sign In</a>
        </div>
        """, unsafe_allow_html=True)
        
        # Hidden button for Streamlit navigation
        if st.button("Sign In", key="sign_in_button", type="secondary", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()


def show_login_page():
    """
    Display the login page with authentication
    Allows existing users to log in with username and password
    """
    apply_auth_styles()
    
    # Center the form with full width
    col1, col2, col3 = st.columns([0.5, 9, 0.5])
    
    with col2:
        # Header with improved spacing
        st.markdown("""
        <div class="auth-header">
            <h1>Login</h1>
            <p>Sign in to access your dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Login form with single column layout
        with st.form("login_form"):
            username = st.text_input(
                "Username or Email", 
                placeholder="Enter your username or email",
                key="login_username"
            )
            
            password = st.text_input(
                "Password", 
                type="password", 
                placeholder="Enter your password",
                key="login_password"
            )
            
            submit_button = st.form_submit_button(
                "Sign In",
                type="primary",
                use_container_width=True
            )
            
            if submit_button:
                # Validation
                if not username or not password:
                    st.error("❌ Please enter both username and password!")
                else:
                    # Attempt authentication
                    success, message, user_data = authenticate_user(username, password)
                    
                    if success:
                        # Set session state
                        st.session_state.logged_in = True
                        st.session_state.user = user_data  # Store user data in session
                        st.session_state.user_data = user_data  # For backward compatibility
                        st.session_state.username = user_data["username"]
                        st.session_state.is_admin = user_data.get("is_admin", False)
                        
                        # Set page to chat
                        st.session_state.page = "chat"
                        
                        # Clear any previous messages
                        if 'messages' not in st.session_state:
                            st.session_state.messages = []
                        
                        # Rerun to update the UI
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        # Divider with text and signup link
        st.markdown("""
        <div style="display: flex; align-items: center; margin: 2rem 0; color: var(--text-secondary);">
            <div style="flex-grow: 1; height: 1px; background: rgba(255, 255, 255, 0.1);"></div>
            <span style="padding: 0 1rem; font-size: 0.9rem; color: rgba(255, 255, 255, 0.5);">or</span>
            <div style="flex-grow: 1; height: 1px; background: rgba(255, 255, 255, 0.1);"></div>
        </div>
        <div style="text-align: center; margin-top: 0.5rem;">
            Don't have an account? <a href="#" style="color: var(--primary); text-decoration: none; font-weight: 500;" onclick="window.parent.document.querySelector('button[data-testid=\"baseButton-secondary\"]').click();">Sign up</a>
        </div>
        """, unsafe_allow_html=True)
        
        # Hidden button for Streamlit navigation
        if st.button("Create Account", key="create_account_button", type="secondary", use_container_width=True):
            st.session_state.auth_page = "signup"
            st.rerun()


def show_auth_page():
    """
    Main authentication page controller
    Manages switching between login and signup pages
    """
    # Initialize auth page state
    if 'auth_page' not in st.session_state:
        st.session_state.auth_page = "login"
    
    # Page configuration
    st.set_page_config(
        page_title="Authentication",
        page_icon="🔐",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # Show appropriate page
    if st.session_state.auth_page == "login":
        show_login_page()
    else:
        show_signup_page()
