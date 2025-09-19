import PyPDF2
import os
from typing import List, Dict
import streamlit as st

class PDFProcessor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.text = ""
        self.pages = []
        
    def extract_text(self) -> str:
        """Extract text from PDF file"""
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    self.pages.append({
                        'page_number': page_num + 1,
                        'text': page_text
                    })
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                
                self.text = text
                return text
                
        except Exception as e:
            st.error(f"Error extracting text from PDF: {str(e)}")
            return ""
    
    def get_pages(self) -> List[Dict]:
        """Get list of pages with their content"""
        return self.pages
    
    def get_text_chunks(self, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into chunks for processing"""
        if not self.text:
            self.extract_text()
        
        chunks = []
        text = self.text
        
        # Split by pages first
        page_splits = text.split("--- Page")
        
        for i, page_content in enumerate(page_splits[1:], 1):  # Skip first empty split
            # Further split large pages into smaller chunks
            if len(page_content) > chunk_size:
                words = page_content.split()
                for j in range(0, len(words), chunk_size - overlap):
                    chunk = " ".join(words[j:j + chunk_size])
                    if chunk.strip():
                        chunks.append(f"Page {i}: {chunk.strip()}")
            else:
                if page_content.strip():
                    chunks.append(f"Page {i}: {page_content.strip()}")
        
        return chunks
