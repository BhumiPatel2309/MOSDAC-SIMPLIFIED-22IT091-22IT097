# MOSDAC SIMPLIFIED

A sophisticated RAG (Retrieval-Augmented Generation) chatbot application built with Streamlit that provides intelligent document querying capabilities using Google's Gemini AI. The system features comprehensive user authentication, admin analytics dashboard, and advanced query processing.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## ✨ Features

### 🔐 Authentication System
- **User Registration & Login**: Secure authentication with bcrypt password hashing
- **Role-Based Access Control**: Separate user and admin dashboards
- **Session Management**: Persistent login sessions with activity tracking

### 💬 Intelligent Chat Interface
- **RAG-Powered Responses**: Context-aware answers using document retrieval
- **Semantic Search**: Advanced sentence-transformer embeddings for accurate document matching
- **Google Gemini AI Integration**: Powered by Gemini Flash for natural language generation
- **Chat History**: Complete conversation tracking with timestamps
- **Response Time Metrics**: Real-time performance monitoring

### 📊 Admin Dashboard
- **User Analytics**: Comprehensive user statistics and activity monitoring
- **Query Analytics**: Track total queries, response times, and usage patterns
- **User Management**: View user details, query counts, and last activity
- **Data Visualization**: Interactive charts and graphs using Plotly
- **Export Capabilities**: Download analytics data in Excel/PDF formats
- **Advanced Metrics**:
  - Daily/hourly usage trends
  - User segmentation (New, Active, Power Users, Inactive)
  - Query complexity distribution
  - Peak usage time analysis

### 👤 User Dashboard
- **Personal Statistics**: View your query count and activity history
- **Recent Activities**: Track your recent interactions
- **Profile Information**: Manage your account details

### 🎨 Modern UI/UX
- **Dark Theme**: Eye-friendly dark mode interface
- **Responsive Design**: Works seamlessly across devices
- **Custom Styling**: Beautiful gradient headers and smooth animations
- **Interactive Components**: Real-time updates and dynamic content

## 🏗️ Architecture

```
┌─────────────────┐
│   Streamlit UI  │
└────────┬────────┘
         │
    ┌────▼─────┐
    │  App.py  │
    └────┬─────┘
         │
    ┌────▼──────────────────────────────┐
    │                                    │
┌───▼────┐  ┌──────────┐  ┌───────────┐
│  Auth  │  │Dashboard │  │ RAG Engine│
│ System │  │  Module  │  │           │
└────────┘  └──────────┘  └─────┬─────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
              ┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐
              │   PDF     │ │ Vector │ │  Gemini  │
              │ Processor │ │ Store  │ │    AI    │
              └───────────┘ └────────┘ └──────────┘
```

## 📦 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Google Gemini API Key ([Get it here](https://makersuite.google.com/app/apikey))
- PDF document (MOSDAC.pdf or your custom document)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/BhumiPatel2309/MOSDAC-SIMPLIFIED-22IT091-22IT097.git
cd MOSDAC-SIMPLIFIED
```

### 2. Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Setup Script

```bash
python setup.py
```

This will:
- Install all required packages
- Create a `.env` file template
- Check for the PDF document

## ⚙️ Configuration

### 1. Environment Variables

Create a `.env` file in the root directory:

```env
# Required: Your Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Override default settings
# MODEL_NAME=gemini-1.5-flash-002
# EMBEDDING_MODEL=all-MiniLM-L6-v2
# CHUNK_SIZE=1000
# CHUNK_OVERLAP=200
```

### 2. PDF Document

Place your PDF document in the root directory and name it `MOSDAC.pdf`, or modify the code to point to your custom PDF location.

### 3. Database

The application automatically creates SQLite databases:
- `users.db`: User authentication and profiles
- `mosdac.db`: Chat history and analytics

## 🎯 Usage

### Starting the Application

#### Method 1: Using the run script (Recommended)

```bash
python run.py
```

#### Method 2: Direct Streamlit command

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

### First Time Setup

1. **Register an Account**
   - Click on "Sign Up"
   - Enter username, email, and password
   - Submit registration

2. **Login**
   - Use your credentials to log in
   - Access the chat interface

3. **Start Chatting**
   - Type your questions in the chat input
   - Get AI-powered responses based on the document content

## 📁 Project Structure

```
MOSDAC-SIMPLIFIED/
│
├── app.py                  # Main Streamlit application
├── auth.py                 # Authentication system
├── dashboard.py            # User and admin dashboards
├── rag_engine.py          # RAG implementation
├── vector_store.py        # Vector database management
├── pdf_processor.py       # PDF parsing and processing
├── config.py              # Configuration settings
├── login_signup.py        # Login/signup UI
├── setup.py               # Setup automation script
├── run.py                 # Application launcher
├── test_db.py             # Database testing utilities
│
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── MOSDAC.pdf            # Your PDF document
│
├── data/                  # Vector store data
│   └── mosdac_vs/        # FAISS index files
│
├── users.db              # User database
├── mosdac.db             # Chat history database
│
└── README.md             # This file
```

## 🛠️ Technologies Used

### Backend
- **Python 3.8+**: Core programming language
- **Streamlit**: Web application framework
- **SQLite**: Database for users and chat history
- **bcrypt**: Password hashing and security

### AI/ML
- **Google Gemini AI**: Language model for response generation
- **LangChain**: Framework for LLM applications
- **Sentence Transformers**: Semantic embeddings
- **FAISS**: Vector similarity search
- **PyPDF2**: PDF document processing

### Frontend
- **Streamlit Components**: UI elements
- **Plotly**: Interactive data visualizations
- **Streamlit-Chat**: Chat interface components
- **Streamlit-Option-Menu**: Navigation menus

### Data Processing
- **Pandas**: Data manipulation and analysis
- **NumPy**: Numerical computations

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Gemini AI for the language model
- Streamlit for the amazing web framework
- LangChain for RAG implementation tools
- The open-source community for various libraries
