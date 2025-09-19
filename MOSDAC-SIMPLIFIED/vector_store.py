import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Tuple
import pickle
import os

class VectorStore:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = 384  # Dimension for all-MiniLM-L6-v2
        self.index = None
        self.texts = []
        self.metadata = []
        
    def create_index(self):
        """Create a new FAISS index"""
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
        
    def add_texts(self, texts: List[str], metadata: List[dict] = None):
        """Add texts to the vector store"""
        if self.index is None:
            self.create_index()
        
        # Generate embeddings
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to index
        self.index.add(embeddings.astype('float32'))
        
        # Store texts and metadata
        self.texts.extend(texts)
        if metadata:
            self.metadata.extend(metadata)
        else:
            self.metadata.extend([{}] * len(texts))
    
    def search(self, query: str, k: int = 5) -> List[Tuple[str, float, dict]]:
        """Search for similar texts"""
        if self.index is None or len(self.texts) == 0:
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_tensor=False)
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding.astype('float32'), k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.texts):
                results.append((
                    self.texts[idx],
                    float(score),
                    self.metadata[idx]
                ))
        
        return results
    
    def save(self, filepath: str):
        """Save the vector store to disk"""
        if self.index is not None:
            faiss.write_index(self.index, f"{filepath}.index")
            
            with open(f"{filepath}.data", 'wb') as f:
                pickle.dump({
                    'texts': self.texts,
                    'metadata': self.metadata
                }, f)
    
    def load(self, filepath: str):
        """Load the vector store from disk"""
        if os.path.exists(f"{filepath}.index") and os.path.exists(f"{filepath}.data"):
            self.index = faiss.read_index(f"{filepath}.index")
            
            with open(f"{filepath}.data", 'rb') as f:
                data = pickle.load(f)
                self.texts = data['texts']
                self.metadata = data['metadata']
            return True
        return False

