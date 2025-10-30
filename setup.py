#!/usr/bin/env python3
"""
MOSDAC RAG Bot - Setup Script
Automated setup and installation script
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    print("📦 Installing required packages...")
    
    # Try with specific versions first
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error with specific versions: {e}")
        print("🔄 Trying with minimal requirements...")
        
        # Try with minimal requirements
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements-minimal.txt"], check=True)
            print("✅ Minimal requirements installed successfully")
            return True
        except subprocess.CalledProcessError as e2:
            print(f"❌ Error installing minimal requirements: {e2}")
            print("💡 Please try installing manually:")
            print("   pip install streamlit langchain google-generativeai faiss-cpu sentence-transformers pypdf2")
            return False

def create_env_file():
    """Create .env file template"""
    env_content = """# MOSDAC RAG Bot Environment Variables
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Override default settings
# MODEL_NAME=gemini-1.5-flash-002
# EMBEDDING_MODEL=all-MiniLM-L6-v2
# CHUNK_SIZE=1000
# CHUNK_OVERLAP=200
"""
    
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write(env_content)
        print("✅ Created .env file template")
        print("📝 Please edit .env file and add your Gemini API key")
    else:
        print("ℹ️ .env file already exists")

def check_pdf():
    """Check if PDF exists and provide instructions"""
    if os.path.exists("MOSDAC.pdf"):
        print("✅ MOSDAC.pdf found")
        return True
    else:
        print("❌ MOSDAC.pdf not found")
        print("📄 Please ensure your PDF file is named 'MOSDAC.pdf' and placed in this directory")
        return False

def main():
    print("🚀 MOSDAC RAG Bot Setup")
    print("=" * 50)
    
    # Install requirements
    if not install_requirements():
        sys.exit(1)
    
    # Create .env file
    create_env_file()
    
    # Check PDF
    pdf_exists = check_pdf()
    
    print("=" * 50)
    print("🎉 Setup completed!")
    print("=" * 50)
    
    if pdf_exists:
        print("✅ Ready to run! Execute: python run.py")
    else:
        print("⚠️ Please add MOSDAC.pdf to the directory, then run: python run.py")
    
    print("\n📚 For more information, see README.md")

if __name__ == "__main__":
    main()
