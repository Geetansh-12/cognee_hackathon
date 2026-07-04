import numpy as np
from fastembed import TextEmbedding
from typing import List, Dict, Any

class NaivePipeline:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model = TextEmbedding(model_name)
        self.facts: List[Dict[str, Any]] = []
        self.embeddings: List[np.ndarray] = []

    def ingest(self, fact_stream: List[Dict[str, Any]]) -> None:
        """
        Naive ingestion: just append everything to the flat list.
        Stale facts are never updated or removed.
        """
        for fact in fact_stream:
            # Create a textual representation of the fact without timestamp to ensure dumbness
            text_representation = f"The {fact['predicate']} of {fact['subject']} is {fact['value']}."
            embedding = list(self.model.embed([text_representation]))[0]
            
            self.facts.append(fact)
            self.embeddings.append(embedding)

    def query(self, question: str, top_k: int = 5) -> str:
        """
        Naive search: embed question, find top-k similar facts, and stuff them in a prompt.
        We return the retrieved context so we can use a standard LLM to generate the answer.
        Since we only need to test the memory layer, returning the exact context text 
        can be used by the grading harness or passed to an LLM. 
        For this benchmark, we will use a simple LLM call.
        """
        if not self.facts:
            return "I don't know."

        question_emb = list(self.model.embed([question]))[0]
        
        # Calculate cosine similarities
        similarities = []
        for emb in self.embeddings:
            # Cosine similarity
            sim = np.dot(question_emb, emb) / (np.linalg.norm(question_emb) * np.linalg.norm(emb))
            similarities.append(sim)
            
        # Get top k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Retrieve context without timestamps so the LLM has no recency signal
        context_parts = []
        for idx in top_indices:
            fact = self.facts[idx]
            context_parts.append(f"- {fact['subject']} {fact['predicate']}: {fact['value']}")
            
        context = "\n".join(context_parts)
        
        # In a full app, this context is passed to an LLM.
        # We will use LiteLLM or OpenAI directly to generate the answer based on the context.
        return context

# Global instance for easy use
_pipeline = NaivePipeline()

def ingest(fact_stream: List[Dict[str, Any]]) -> None:
    _pipeline.ingest(fact_stream)

def query(question: str) -> str:
    from openai import OpenAI
    import os
    
    context = _pipeline.query(question)
    
    # We will use a basic LLM prompt to answer the question using the context.
    # Assumes OPENAI_API_KEY is set, or we can use litellm.
    # For now, let's use a simple mock if no key, or real if key exists.
    # Wait, the prompt says "Whatever Cognee is already configured to use ... use the same LLM".
    # Cognee uses litellm by default under the hood or similar. Let's just use litellm directly.
    import litellm
    import os
    from tenacity import retry, stop_after_attempt, wait_exponential

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
    def call_llm():
        model_name = os.getenv("LLM_MODEL", "groq/llama3-8b-8192")
        return litellm.completion(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Answer the question based ONLY on the provided context. Be concise."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ]
        )

    try:
        response = call_llm()
        return response.choices[0].message.content
    except Exception as e:
        # Fallback to just returning context if LLM call fails
        return f"Context:\n{context}\n\n(LLM Error: {e})"
