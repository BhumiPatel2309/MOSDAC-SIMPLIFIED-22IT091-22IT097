import re, numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, util
import google.generativeai as genai
from config import GEMINI_API_KEY

class RAGEngine:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        # Use strong embedding model for semantic similarity
        self.sim_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        # Check if the similarity model is available
        try:
            # Test if model loads successfully
            test_emb = self.sim_model.encode(["test"], normalize_embeddings=True)
            self.sim_model_available = True
        except Exception:
            # Model loading errors
            self.sim_model_available = False
        
        # Initialize Gemini AI for answer generation
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            # Use gemini-flash-latest which is stable and supports v1 API
            self.gemini_model = genai.GenerativeModel('models/gemini-flash-latest')
            self.gemini_available = True
        except Exception as e:
            print(f"Warning: Gemini AI initialization failed: {e}")
            self.gemini_available = False

    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences and filter short/noisy ones"""
        s = re.split(r'(?<=[.!?])\s+', text.strip())
        # clean and filter very short/noisy
        return [t.strip() for t in s if len(t.strip()) > 15]

    def pick_best_sentences(self, query: str, contexts: List[str], n: int = 3) -> List[str]:
        """Pick top n best sentences based on semantic similarity with query"""
        if not self.sim_model_available:
            return []
        # Embed query and candidate sentences, pick highest cosine similarities
        q_emb = self.sim_model.encode([query], normalize_embeddings=True)
        s_emb = self.sim_model.encode(contexts, normalize_embeddings=True)
        sims = util.cos_sim(q_emb, s_emb).cpu().numpy()[0]
        # Get indices of top n most similar sentences
        top_indices = np.argsort(sims)[-n:][::-1]  # Get top n indices in descending order
        return [contexts[idx] for idx in top_indices]

    def retrieve_relevant_docs(self, query: str, k: int = 6) -> List[str]:
        """Retrieve relevant documents from vector store"""
        results = self.vector_store.search(query, k)
        return [result[0] for result in results]

    def construct_detailed_answer(self, query: str, sentences: List[str], threshold: float = 0.3) -> str:
        """Construct a detailed, contextually coherent answer from multiple sentences"""
        if not sentences:
            return "I couldn't find this information in the document."

        # Filter sentences by relevance threshold
        relevant_sentences = []
        q_emb = self.sim_model.encode([query], normalize_embeddings=True)
        for sentence in sentences:
            s_emb = self.sim_model.encode([sentence], normalize_embeddings=True)
            similarity = util.cos_sim(q_emb, s_emb).cpu().numpy()[0][0]
            if similarity >= threshold:
                relevant_sentences.append((sentence, similarity))

        if not relevant_sentences:
            return "I couldn't find this information in the document."

        # Sort by relevance and take top sentences
        relevant_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [sent for sent, _ in relevant_sentences[:3]]  # Take top 3

        # Combine sentences into a coherent answer
        if len(top_sentences) == 1:
            return top_sentences[0]
        else:
            # Combine multiple sentences for more detailed answer
            combined_answer = top_sentences[0]
            # Add additional context if sentences are related
            for sent in top_sentences[1:]:
                # Check if this sentence adds new information
                if sent.lower() not in combined_answer.lower():
                    combined_answer += " " + sent
            return combined_answer

    def generate_response(self, query: str, context_docs: List[str] = None) -> str:
        """Generate a response using Google Gemini AI"""
        if not self.gemini_available:
            return self._fallback_generate_response(query, context_docs or [])
            
        try:
            # Use a more direct and concise prompt
            prompt = f"""Please provide a clear, helpful, and informative answer to the following question.
            
            Question: {query}
            
            Guidelines:
            - Be direct and to the point
            - Use your general knowledge to provide the best possible answer
            - Keep it concise but informative (1-2 paragraphs)
            - If you're not certain, provide the most likely information
            - Never mention documents, data sources, or system limitations
            - Never say you don't have enough information
            - Sound confident and natural in your response
            
            Answer:"""
            
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            print(f"Gemini API error: {e}")
            return self._fallback_generate_response(query, context_docs or [])
    
    def _is_context_insufficient(self, query: str, context_docs: List[str], threshold: float = 0.3) -> bool:
        """Always return True to ensure we use Gemini's knowledge"""
        return True
        
    def _fallback_generate_response(self, query: str, context_docs: List[str] = None) -> str:
        """Fallback method that provides a helpful response using general knowledge"""
        if not self.gemini_available:
            return "I'd be happy to help with that! Please try again in a moment."
            
        try:
            prompt = f"""Please provide a helpful and informative answer to the following question.
            
            Question: {query}
            
            Guidelines:
            - Be direct and helpful
            - Use your general knowledge
            - Keep it concise (1-2 paragraphs)
            - If unsure, provide the most likely information
            - Never mention documents, data sources, or technical limitations
            - Sound confident and natural
            
            Answer:"""
            
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            print(f"Gemini API error in fallback: {e}")
            return "I'd be happy to help with that! Please try again in a moment."

    def is_weather_query(self, question: str) -> bool:
        """Check if the question is about weather forecast"""
        weather_terms = ['weather', 'forecast', 'temperature', 'rain', 'sunny', 'cloudy', 'humidity',
                        'precipitation', 'wind', 'climate', 'temperature', 'degree', '°C', '°F']
        return any(term in question.lower() for term in weather_terms)

    def query(self, question: str, k: int = 6) -> Dict[str, Any]:
        """Main query method that retrieves and generates response"""
        # For weather queries, skip document retrieval and use Gemini directly
        if self.is_weather_query(question):
            if self.gemini_available:
                try:
                    prompt = f"""You are a professional weather forecaster. Please provide a helpful and informative weather forecast based on the following question:
                    
                    Question: {question}
                    
                    Guidelines for your response:
                    1. Provide a clear and direct weather forecast
                    2. Include relevant details like temperature, precipitation, wind, and general conditions
                    3. If specific location is mentioned, provide location-specific forecast
                    4. Keep the response concise but informative (2-3 paragraphs maximum)
                    5. Use a friendly and professional tone
                    6. Present the information as if you're a weather expert providing a forecast
                    7. If you don't have specific data, provide a general forecast based on seasonal patterns
                    
                    Weather forecast:"""
                    response = self.gemini_model.generate_content(prompt)
                    return {
                        "question": question,
                        "response": response.text.strip(),
                        "relevant_docs": [],
                        "num_docs_retrieved": 0,
                        "gemini_available": True
                    }
                except Exception as e:
                    print(f"Gemini API error in weather query: {e}")
        
        # For non-weather queries, use the standard flow
        relevant_docs = self.retrieve_relevant_docs(question, k)
        response = self.generate_response(question, relevant_docs)

        return {
            "question": question,
            "response": response,
            "relevant_docs": relevant_docs,
            "num_docs_retrieved": len(relevant_docs),
            "gemini_available": self.gemini_available
        }
