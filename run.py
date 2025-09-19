#!/usr/bin/env python3
"""
MOSDAC RAG Bot - Run Script
Simple script to launch the Streamlit application
"""

import subprocess
import sys
import os

def check_requirements():
    """Check if required packages are installed"""
    try:
        import streamlit
        import openai
        import faiss
        import sentence_transformers
        import PyPDF2
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_pdf():
    """Check if MOSDAC.pdf exists"""
    if os.path.exists("MOSDAC.pdf"):
        print("✅ MOSDAC.pdf found")
        return True
    else:
        print("❌ MOSDAC.pdf not found in current directory")
        return False

def main():
    print("🚀 Starting MOSDAC RAG Bot...")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check PDF
    if not check_pdf():
        print("Please ensure MOSDAC.pdf is in the current directory")
        sys.exit(1)
    
    print("=" * 50)
    print("🌐 Launching Streamlit application...")
    print("📱 The app will open in your default browser")
    print("🔗 URL: http://localhost:8501")
    print("=" * 50)
    
    # Launch Streamlit
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

