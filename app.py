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

# Page configuration
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state=INITIAL_SIDEBAR_STATE
)

# Custom CSS for attractive light theme UI
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .main {
        font-family: 'Inter', sans-serif;
    }
    
    /* Light Theme Header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
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
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .main-header p {
        font-size: 1.2rem;
        font-weight: 300;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Chat Messages */
    .stChatMessage {
        background: #ffffff;
        border-radius: 16px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #e1e5e9;
        color: #000000;
    }
    /* Enforce black for all nested text inside chat messages */
    .stChatMessage * { color: #000000 !important; }
    .stChatMessage a { color: #000000 !important; text-decoration: underline; }

    /* Make top nav tab text black in all states */
    .stTabs [data-baseweb="tab"] { color: #000000 !important; }
    .stTabs [aria-selected="true"] { color: #000000 !important; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
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
    """Display the chat interface"""
    # Chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about MOSDAC..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if st.session_state.rag_engine:
                    result = st.session_state.rag_engine.query(prompt)
                    response = result["response"]
                else:
                    response = "System not ready. Ensure MOSDAC.pdf exists and API key is set."
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})


def main():
    # Header
    st.markdown("""
    <div class="main-header fade-in">
        <h1>🤖 MOSDAC SIMPLIFIED</h1>
        <p>Meteorological & Oceanographic Satellite Data Archival Centre</p>    
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        
        # System auto-initializes silently
        
        # Settings removed - using defaults from config
        
        # Clear chat
        if st.button("🗑️ Clear Chat History", help="Clear all chat messages"):
            st.session_state.messages = []
            st.rerun()
        
        # Additional info
        st.markdown("""
        <div class="sidebar-content">
            <h4 style="color: #667eea; margin-bottom: 0.5rem;">ℹ️ Quick Info</h4>
            <p style="font-size: 0.8rem; color: #6c757d; margin: 0;">
MOSDAC (Meteorological & Oceanographic Satellite Data Archival Centre) by ISRO-SAC is a hub for satellite data on weather, ocean, and climate. It provides real-time and archived datasets to support research, forecasting, and societal applications.            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Main content area
    selected = option_menu(
        menu_title=None,
        options=["Chat", "About"],
        icons=["chat", "info-circle"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "#fafafa"},
            "icon": {"color": "orange", "font-size": "25px"},
            "nav-link": {
                "font-size": "16px",
                "text-align": "left",
                "margin": "0px",
                "--hover-color": "#eee",
                "color": "#000000"
            },
            "nav-link-selected": {"background-color": "#667eea", "color": "#000000"},
        }
    )
    
    if selected == "Chat":
        # Auto-initialize once per app run after functions exist
        if not st.session_state.initialized:
            with st.spinner("Initializing system..."):
                initialize_system()
            st.session_state.initialized = True
        display_chat_interface()
    
    elif selected == "About":
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


if __name__ == "__main__":
    main()
