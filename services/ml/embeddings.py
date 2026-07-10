"""
Semantic Embeddings Service for INDB

Converts abstract tokens to semantic vector space using sentence-transformers.
Enables semantic similarity instead of simple Jaccard index.
"""

from typing import List, Dict, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


class SemanticEmbeddings:
    """
    Semantic embedding service for INDB tokens.
    
    Converts token lists to dense vector representations,
    enabling semantic similarity calculations.
    """
    
    _model_cache = {}
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize embeddings service.
        
        Args:
            model_name: Sentence-transformers model name
                       'all-MiniLM-L6-v2' - Fast, 384 dimensions
                       'all-mpnet-base-v2' - Better quality, 768 dimensions
        """
        if not ML_AVAILABLE:
            raise ImportError("sentence-transformers required for SemanticEmbeddings")
        
        self.model_name = model_name
        
        # Use cached model if available
        if model_name in SemanticEmbeddings._model_cache:
            self.model = SemanticEmbeddings._model_cache[model_name]
        else:
            self.model = SentenceTransformer(model_name)
            SemanticEmbeddings._model_cache[model_name] = self.model
            
        self.embeddings_cache = {}
    
    def get_embedding(self, tokens: List[str]) -> np.ndarray:
        """
        Get embedding vector for token list.
        
        Args:
            tokens: List of abstract tokens
            
        Returns:
            Dense embedding vector
        """
        # Convert tokens to text
        text = ' '.join(tokens)
        
        # Check cache
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]
        
        # Generate embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        # Cache
        self.embeddings_cache[text] = embedding
        
        return embedding
    
    def calculate_similarity(self, tokens1: List[str], tokens2: List[str]) -> float:
        """
        Calculate semantic similarity between two token lists.
        
        Args:
            tokens1: First token list
            tokens2: Second token list
            
        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        emb1 = self.get_embedding(tokens1)
        emb2 = self.get_embedding(tokens2)
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        
        # Normalize to 0-1 range
        similarity = (similarity + 1) / 2
        
        return float(similarity)
    
    def find_similar_tokens(
        self, 
        query_tokens: List[str], 
        candidate_tokens_list: List[List[str]], 
        top_k: int = 5,
        threshold: float = 0.5
    ) -> List[Dict[str, any]]:
        """
        Find most similar token lists to query.
        
        Args:
            query_tokens: Query token list
            candidate_tokens_list: List of candidate token lists
            top_k: Number of top results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of {tokens, similarity} dictionaries
        """
        query_emb = self.get_embedding(query_tokens)
        
        similarities = []
        for candidate_tokens in candidate_tokens_list:
            candidate_emb = self.get_embedding(candidate_tokens)
            similarity = np.dot(query_emb, candidate_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(candidate_emb)
            )
            similarity = (similarity + 1) / 2  # Normalize
            
            if similarity >= threshold:
                similarities.append({
                    'tokens': candidate_tokens,
                    'similarity': float(similarity)
                })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similarities[:top_k]
    
    def cluster_tokens(
        self, 
        tokens_list: List[List[str]], 
        n_clusters: int = 5
    ) -> Dict[int, List[int]]:
        """
        Cluster token lists by semantic similarity.
        
        Args:
            tokens_list: List of token lists
            n_clusters: Number of clusters
            
        Returns:
            Dictionary mapping cluster_id to list of indices
        """
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            raise ImportError("scikit-learn required for clustering")
        
        # Get embeddings for all token lists
        embeddings = np.array([self.get_embedding(tokens) for tokens in tokens_list])
        
        # Cluster
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(embeddings)
        
        # Group by cluster
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
        
        return clusters
    
    def expand_query(
        self, 
        query_tokens: List[str], 
        vocabulary: List[str], 
        top_k: int = 5
    ) -> List[str]:
        """
        Expand query with semantically similar tokens.
        
        Args:
            query_tokens: Original query tokens
            vocabulary: Available vocabulary
            top_k: Number of similar tokens to add
            
        Returns:
            Expanded token list
        """
        query_emb = self.get_embedding(query_tokens)
        
        # Get embeddings for vocabulary
        vocab_similarities = []
        for token in vocabulary:
            if token in query_tokens:
                continue
            
            token_emb = self.get_embedding([token])
            similarity = np.dot(query_emb, token_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(token_emb)
            )
            
            vocab_similarities.append((token, float(similarity)))
        
        # Sort and get top-k
        vocab_similarities.sort(key=lambda x: x[1], reverse=True)
        expanded_tokens = [token for token, _ in vocab_similarities[:top_k]]
        
        return query_tokens + expanded_tokens
    
    def clear_cache(self):
        """Clear embeddings cache."""
        self.embeddings_cache.clear()
    
    def cache_size(self) -> int:
        """Get number of cached embeddings."""
        return len(self.embeddings_cache)
