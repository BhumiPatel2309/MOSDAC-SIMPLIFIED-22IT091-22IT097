import google.generativeai as genai
from typing import List, Dict
import streamlit as st
from config import GEMINI_API_KEY, MODEL_NAME, MAX_TOKENS, TEMPERATURE

class RAGEngine:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(MODEL_NAME)
        else:
            self.model = None
        
    def retrieve_relevant_docs(self, query: str, k: int = 5) -> List[str]:
        """Retrieve relevant documents from vector store"""
        results = self.vector_store.search(query, k)
        return [result[0] for result in results]
    
    def generate_response(self, query: str, context_docs: List[str]) -> str:
        """Generate response using Google Gemini API with retrieved context"""
        if not GEMINI_API_KEY:
            return "Please set your Gemini API key in the environment variables or .env file."
        
        if not self.model:
            return "Gemini model not initialized. Please check your API key."
        
        # Create context from retrieved documents
        context = "\n\n".join(context_docs)
        
        # Create the prompt
        prompt = f"""You are a helpful assistant for MOSDAC (Ministry of Statistics and Programme Implementation Data Analysis Center). 
        Use the following context to answer the user's question. If the answer is not in the context, say so.

        Context:
        {context}

        Question: {query}

        Answer:"""
        
        try:
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text.strip()
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def query(self, question: str, k: int = 5) -> Dict[str, any]:
        """Main query method that retrieves and generates response"""
        # Retrieve relevant documents
        relevant_docs = self.retrieve_relevant_docs(question, k)
        
        # Generate response
        response = self.generate_response(question, relevant_docs)
        
        return {
            "question": question,
            "response": response,
            "relevant_docs": relevant_docs,
            "num_docs_retrieved": len(relevant_docs)
        }
