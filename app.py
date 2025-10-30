import streamlit as st
import os
import time
from streamlit_chat import message
from streamlit_option_menu import option_menu
import plotly.express as px
import pandas as pd
import numpy as np

from pdf_processor import PDFProcessor
from vector_store import VectorStore
from rag_engine import RAGEngine
from config import *
from pathlib import Path
from login_signup import show_auth_page
from dashboard import show_user_dashboard, show_admin_dashboard, log_chat, log_activity

# Page configuration
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state=INITIAL_SIDEBAR_STATE
)

# Custom CSS for dark theme UI
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Dark Theme */
    :root {
        --primary: #7c4dff;
        --primary-dark: #651fff;
        --secondary: #1e1e2d;
        --dark: #121212;
        --darker: #0a0a0a;
        --light: #e0e0e0;
        --lighter: #f5f5f5;
        --text: #ffffff;
        --text-secondary: #b0b0b0;
    }
    
    /* Base Styles */
    .stApp {
        background-color: var(--dark) !important;
        color: var(--text) !important;
    }
    
    .main {
        font-family: 'Inter', sans-serif;
        background-color: var(--dark);
        color: var(--text);
    }
    
    /* Header Styles */
    .main-header {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        position: relative;
        overflow: hidden;
        border: none;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, rgba(255,255,255,0.1) 0%, transparent 100%);
        pointer-events: none;
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        color: white;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        font-size: 1.2rem;
        font-weight: 300;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        color: rgba(255, 255, 255, 0.9);
    }
    
    /* Chat Messages */
    .stChatMessage {
        background: var(--secondary) !important;
        border-radius: 16px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: var(--text) !important;
    }
    
    /* Text and Links */
    body, .stTextInput>div>div>input, .stTextInput>div>div>textarea,
    .stSelectbox>div>div>div>div>div, .stNumberInput>div>div>input,
    .stSlider>div>div>div>div>div>div {
        color: var(--text) !important;
    }
    
    /* Sidebar */
    .css-1d391kg, .css-1vq4p4l {
        background-color: var(--darker) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Input Fields */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea,
    .stSelectbox>div>div>div>div>div {
        background-color: var(--secondary) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: var(--text) !important;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: var(--primary) !important;
        color: white !important;
        border: none !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton>button:hover {
        background-color: var(--primary-dark) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        color: var(--text-secondary) !important;
        background-color: transparent !important;
    }
    
    .stTabs [aria-selected="true"] {
        color: var(--primary) !important;
        background-color: rgba(124, 77, 255, 0.1) !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--darker);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-dark);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for authentication
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

# Initialize session state for app functionality
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None
if 'rag_engine' not in st.session_state:
    st.session_state.rag_engine = None
if 'pdf_processed' not in st.session_state:
    st.session_state.pdf_processed = False

# Ensure one-time initialization per app run (not every Streamlit rerun)
if 'initialized' not in st.session_state:
    st.session_state.initialized = False


def initialize_system():
    """Initialize the RAG system"""
    try:
        # Ensure persistence directory
        vs_dir = Path(VECTOR_STORE_DIR)
        vs_dir.mkdir(parents=True, exist_ok=True)
        vs_path = vs_dir / VECTOR_STORE_NAME

        # Check if PDF exists
        pdf_path = "MOSDAC.pdf"
        if not os.path.exists(pdf_path):
            st.error("MOSDAC.pdf not found in the current directory.")
            return False
        
        vector_store = VectorStore(EMBEDDING_MODEL)
        # Try load cached vector store
        loaded = vector_store.load(str(vs_path))
        if not loaded:
            # Process PDF and build index once
            with st.spinner("Processing PDF and building vector index (first run only)..."):
                pdf_processor = PDFProcessor(pdf_path)
                text = pdf_processor.extract_text()
                
                if not text:
                    st.error("Failed to extract text from PDF.")
                    return False
                
                # Create chunks
                chunks = pdf_processor.get_text_chunks(CHUNK_SIZE, CHUNK_OVERLAP)
                
                # Build index
                vector_store.add_texts(chunks)
                # Save for reuse
                vector_store.save(str(vs_path))
            
        # Create RAG engine
        rag_engine = RAGEngine(vector_store)
        
        # Store in session state
        st.session_state.vector_store = vector_store
        st.session_state.rag_engine = rag_engine
        st.session_state.pdf_processed = True
            
        return True
        
    except Exception as e:
        st.error(f"Error initializing system: {str(e)}")
        return False


def display_chat_interface():
    """Display the chat interface with input at the bottom"""
    # Create a container for chat messages
    chat_container = st.container()
    
    # Display chat history
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Fixed chat input at the bottom
    st.markdown("""
    <style>
        .fixed-bottom {
            position: fixed;
            bottom: 2rem;
            left: 2rem;
            right: 2rem;
            z-index: 1000;
            background: var(--darker);
            padding: 1rem 0;
            margin-top: 2rem;
        }
        @media (max-width: 768px) {
            .fixed-bottom {
                left: 1rem;
                right: 1rem;
                bottom: 1rem;
            }
        }
    </style>
    <div class="fixed-bottom">
    """, unsafe_allow_html=True)
    
    # Chat input - this will be at the bottom
    if prompt := st.chat_input("Ask me anything about MOSDAC..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Rerun to update the chat display
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # If there's a new message, process and add the assistant's response
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        user_message = st.session_state.messages[-1]["content"]
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    if st.session_state.rag_engine:
                        result = st.session_state.rag_engine.query(user_message)
                        response = result["response"]
                    else:
                        response = "System not ready. Ensure MOSDAC.pdf exists and API key is set."
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})


def show_welcome_page():
    """Display welcome page with About MOSDAC information after successful login"""
    st.markdown("""
    <div style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 30vh;
        text-align: center;
        margin-bottom: 2rem;
    ">
        <h1 style="
            font-size: 4rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
        ">Welcome to MOSDAC-Simplified!</h1>
        <p style="
            font-size: 1.5rem;
            color: #6c757d;
            margin-top: 1rem;
        ">Start exploring meteorological and oceanographic data</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Add About MOSDAC content
    st.markdown("""
### 🌐 About MOSDAC

MOSDAC (Meteorological & Oceanographic Satellite Data Archival Centre) is an initiative of the Space Applications Centre (SAC), Indian Space Research Organisation (ISRO), Ahmedabad.

It is a dedicated data archive and service portal for satellite data and related products focused on meteorology, oceanography, and tropical weather. MOSDAC acts as a gateway for space-based information, enabling researchers, students, institutions, and decision-makers to utilize satellite data for scientific research, operational services, and societal applications.

### 📌 Key Objectives of MOSDAC
- 🛰️ **Archival & Dissemination of Data**: Securely store and provide access to satellite data for long-term usage.
- 🌦️ **Support for Weather & Climate Services**: Provide data that enhances weather forecasting, climate monitoring, and disaster management.
- 🌊 **Oceanographic Applications**: Enable ocean state forecasting, cyclone tracking, fisheries, and coastal management.
- 🔬 **Research Facilitation**: Empower scientists, students, and developers with high-quality datasets for innovative applications.
- 📡 **Real-time Data Access**: Ensure that operational agencies can use near-real-time data for quick decision-making.

### 🌍 Types of Data & Services Available
1. **Meteorological Data**
   - Weather parameters (clouds, temperature, humidity, rainfall)
   - Monsoon studies
   - Cyclone monitoring and tracking
2. **Oceanographic Data**
   - Sea surface temperature
   - Ocean color (chlorophyll, productivity)
   - Ocean waves and currents
   - Coastal monitoring
3. **Atmospheric & Climate Data**
   - Climate variability studies
   - Long-term datasets for research
   - Extreme weather event analysis
4. **Satellite Missions Covered**
   - INSAT Series
   - Oceansat Series
   - Megha-Tropiques
   - Scatsat-1
   - Other ISRO meteorology & oceanography satellites

### 🎯 Applications of MOSDAC Data
- Weather Forecasting – Improved short, medium, and long-range forecasts.
- Disaster Management – Early warning for cyclones, floods, and extreme weather.
- Agriculture – Rainfall monitoring, crop assessment, drought prediction.
- Fisheries & Coastal Management – Ocean productivity and fishery zone advisories.
- Climate Research – Long-term climate variability and global warming studies.
- Education & Training – Helping students and researchers understand earth systems.

### 🤖 About This Chatbot
This chatbot has been created to simplify access to MOSDAC information. Instead of browsing multiple sections, you can ask your queries directly here.

With this chatbot, you can:
- 🔍 Search for available data and datasets.
- 📂 Learn how to access MOSDAC portals.
- 🌦️ Get explanations about weather, ocean, and climate-related parameters.
- 🎓 Understand the role of ISRO satellites in meteorology and oceanography.
- 💡 Receive educational help for research and student projects.

### 🚀 Why MOSDAC Matters
Satellite data is critical for India and the world to monitor our atmosphere, oceans, and climate. By providing free and accessible datasets, MOSDAC bridges the gap between space technology and real-world applications, ensuring that information from space benefits everyone — from farmers to scientists, from students to policymakers.

✨ Start chatting in the chat section to explore the world of MOSDAC data and services in a simple, interactive way!
    """)


def main():
    # Set page config - must be the first Streamlit command
    st.set_page_config(
        page_title="MOSDAC Simplified",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Check if user is logged in
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Show login page if not logged in
    if not st.session_state.logged_in:
        # Apply custom styles for auth pages
        st.markdown("""
        <style>
            /* Full page background */
            .stApp {
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%) !important;
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            /* Center the auth container */
            .block-container {
                max-width: 500px !important;
                padding: 0 !important;
            }
            
            /* Remove extra spacing */
            .stApp > div:first-child {
                width: 100%;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Show auth page
        from login_signup import show_auth_page
        show_auth_page()
        return
    
    # Custom CSS for main app
    st.markdown("""
    <style>
        /* Main header styling */
        .main-header {
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
            padding: 1.5rem;
            margin: -1rem -1rem 2rem -1rem;
            color: white;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .main-header h1 {
            font-size: 2.2rem;
            margin-bottom: 0.5rem;
            letter-spacing: 1px;
        }
        
        .main-header p {
            font-size: 1.1rem;
            opacity: 0.9;
            margin: 0;
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            margin-bottom: 1.5rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: #f5f5f5;
            border-radius: 8px 8px 0 0;
            padding: 0.75rem 1.5rem;
            font-weight: 500;
            color: #555;
            transition: all 0.2s;
            border: none;
            margin: 0;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background: #e0e0e0;
            color: #333;
        }
        
        .stTabs [aria-selected="true"] {
            background: #fff;
            color: #1a237e;
            font-weight: 600;
            box-shadow: 0 -2px 0 #1a237e inset;
        }
        
        .stTabs [data-baseweb="tab-panel"] {
            padding: 1.5rem 0;
        }
        
        /* Chat message styling */
        .stChatMessage {
            margin: 0.5rem 0;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            background: #f8f9fa;
        }
        
        /* Input area */
        .stTextInput > div > div > input {
            border-radius: 8px !important;
            padding: 0.75rem 1rem !important;
            border: 1px solid #ddd !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>MOSDAC SIMPLIFIED</h1>
        <p>Meteorological & Oceanographic Satellite Data Archival Centre</p>    
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        # Add a nice header to the sidebar with user info
        st.markdown(f"""
        <div style="text-align: center;">
            <h2 style="color: #667eea; margin-bottom: 0;">MOSDAC</h2>
            <p style="color: #6c757d; margin-top: 0;">Welcome, {st.session_state.get('username', 'User')}!</p>
        </div>
        <hr style="margin: 1rem 0;">
        """, unsafe_allow_html=True)
        
        # Add logout button
        if st.button("Sign Out", use_container_width=True, key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.messages = []
            st.rerun()
        
        # Clear chat
        if st.button("🗑️ Clear Chat History", help="Clear all chat messages"):
            st.session_state.messages = []
            st.rerun()
        
        # Additional info
        st.markdown("""
        <div class="sidebar-content">
            <h4 style="color: #667eea; margin-bottom: 0.5rem;">ℹ️ Quick Info</h4>
            <p style="font-size: 0.8rem; color: #6c757d; margin: 0;">
                MOSDAC (Meteorological & Oceanographic Satellite Data Archival Centre) by ISRO-SAC is a hub for satellite data on weather, ocean, and climate. It provides real-time and archived datasets to support research, forecasting, and societal applications.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Main content area with navigation
    st.markdown("""
    <style>
        /* Style the navigation tabs */
        .stTabs [data-baseweb="tab-list"] {
            justify-content: center;
            margin-bottom: 1.5rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0.5rem 2rem;
            border-radius: 20px;
            margin: 0 0.5rem;
            transition: all 0.3s ease;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #667eea !important;
            color: white !important;
        }
        
        .stTabs [aria-selected="false"] {
            background-color: #f0f2f6 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Create tabs for navigation based on user
    if 'username' in st.session_state:
        # Regular user view with 2 tabs for all users including 'bhumi'
        tab1, tab2 = st.tabs(["💬 Chat", "ℹ️ About"])
        
        with tab1:
            if not st.session_state.initialized:
                with st.spinner("Initializing system..."):
                    initialize_system()
                st.session_state.initialized = True
            display_chat_interface()
            
        with tab2:
            show_welcome_page()
    else:
        # Regular user view with 2 tabs
        tab1, tab2 = st.tabs(["💬 Chat", "ℹ️ About"])
        
        with tab1:
            if not st.session_state.initialized:
                with st.spinner("Initializing system..."):
                    initialize_system()
                st.session_state.initialized = True
            display_chat_interface()
            
        with tab2:
            show_welcome_page()


if __name__ == "__main__":
    main()
