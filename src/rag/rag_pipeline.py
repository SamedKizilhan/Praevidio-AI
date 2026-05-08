"""
Praevidio AI - RAG Pipeline (Retrieval-Augmented Generation)
=============================================================
Indexes the ICD-10 knowledge base into ChromaDB and provides
symptom-to-ICD-10 code retrieval using semantic search.

Two modes:
  - Embedding mode: Uses OpenAI text-embedding-3-small (requires API key)
  - Demo mode: Uses keyword matching (offline, no API needed)
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    KNOWLEDGE_BASE_DIR, CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL, OPENAI_API_KEY
)


def load_knowledge_base() -> list[dict]:
    """
    Load and flatten the ICD-10 knowledge base into documents
    suitable for vector store indexing.

    Each document contains:
      - id: ICD-10 code or feature name
      - text: Searchable text combining descriptions, TR terms, voice descriptors
      - metadata: Structured fields for retrieval
    """
    documents = []

    # --- Load ICD-10 codes ---
    icd10_path = KNOWLEDGE_BASE_DIR / "icd10_lung_codes.json"
    with open(icd10_path, "r", encoding="utf-8") as f:
        icd10_data = json.load(f)

    # Index symptoms
    for code, info in icd10_data.get("symptoms", {}).items():
        voice_terms = info.get("voice_descriptors_tr", [])
        text = (
            f"ICD-10 Code: {code}. "
            f"{info['description']}. "
            f"{info['description_tr']}. "
            f"Clinical: {info.get('clinical_significance', '')}. "
            f"Turkish terms: {', '.join(voice_terms)}."
        )
        documents.append({
            "id": code,
            "text": text,
            "metadata": {
                "type": "symptom",
                "code": code,
                "description": info["description"],
                "description_tr": info["description_tr"],
                "dataset_mapping": info.get("dataset_mapping"),
                "voice_descriptors_tr": json.dumps(voice_terms, ensure_ascii=False),
            }
        })

    # Index risk factors
    for code, info in icd10_data.get("risk_factors", {}).items():
        voice_terms = info.get("voice_descriptors_tr", [])
        text = (
            f"ICD-10 Code: {code}. "
            f"{info['description']}. "
            f"{info['description_tr']}. "
            f"Clinical: {info.get('clinical_significance', '')}. "
            f"Turkish terms: {', '.join(voice_terms)}."
        )
        documents.append({
            "id": code,
            "text": text,
            "metadata": {
                "type": "risk_factor",
                "code": code,
                "description": info["description"],
                "description_tr": info["description_tr"],
                "dataset_mapping": info.get("dataset_mapping"),
                "voice_descriptors_tr": json.dumps(voice_terms, ensure_ascii=False),
            }
        })

    # Index primary diagnosis subcodes
    for code, info in icd10_data.get("primary_diagnosis", {}).get("C34", {}).get("subcodes", {}).items():
        text = (
            f"ICD-10 Code: {code}. "
            f"Lung cancer subtype: {info['description']}. "
            f"{info['description_tr']}. "
            f"{info.get('notes', '')}"
        )
        documents.append({
            "id": code,
            "text": text,
            "metadata": {
                "type": "diagnosis",
                "code": code,
                "description": info["description"],
                "description_tr": info["description_tr"],
            }
        })

    # --- Load symptom-risk factor mappings ---
    srf_path = KNOWLEDGE_BASE_DIR / "symptom_risk_factors.json"
    with open(srf_path, "r", encoding="utf-8") as f:
        srf_data = json.load(f)

    for feature in srf_data.get("features", []):
        doc_id = f"SRF_{feature['name']}"
        text = (
            f"Feature: {feature['name']}. "
            f"ICD-10: {feature.get('icd10', 'N/A')}. "
            f"Type: {feature['type']}. "
            f"Category: {feature['category']}. "
            f"Weight: {feature['weight']}. "
            f"Clinical: {feature.get('clinical_notes', '')}."
        )
        documents.append({
            "id": doc_id,
            "text": text,
            "metadata": {
                "type": feature["type"],
                "code": feature.get("icd10", ""),
                "description": feature["name"],
                "description_tr": feature.get("clinical_notes", ""),
                "dataset_mapping": feature["name"],
                "weight": feature["weight"],
            }
        })

    return documents


def build_index(force_rebuild: bool = False) -> "chromadb.Collection":
    """
    Build or load the ChromaDB vector store index.

    Args:
        force_rebuild: If True, delete existing collection and rebuild.

    Returns:
        ChromaDB collection object.
    """
    import chromadb
    from chromadb.utils import embedding_functions

    print("📦 RAG Pipeline — Building Vector Index")
    print("=" * 50)

    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    # Check if collection exists
    existing = [c.name for c in client.list_collections()]
    if CHROMA_COLLECTION_NAME in existing and not force_rebuild:
        print(f"   ✅ Collection '{CHROMA_COLLECTION_NAME}' already exists, loading...")
        collection = client.get_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=_get_embedding_function()
        )
        print(f"   📊 {collection.count()} documents indexed")
        return collection

    # Delete if rebuilding
    if CHROMA_COLLECTION_NAME in existing:
        client.delete_collection(CHROMA_COLLECTION_NAME)
        print(f"   🗑️  Deleted existing collection")

    # Create new collection
    embed_fn = _get_embedding_function()
    collection = client.create_collection(
        name=CHROMA_COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"description": "Praevidio AI ICD-10 Knowledge Base"}
    )

    # Load and index documents
    documents = load_knowledge_base()
    print(f"   📄 Loaded {len(documents)} documents from knowledge base")

    # Sanitize metadata (ChromaDB doesn't accept None values)
    sanitized_metadatas = []
    for doc in documents:
        clean_meta = {}
        for k, v in doc["metadata"].items():
            if v is None:
                clean_meta[k] = ""
            else:
                clean_meta[k] = v
        sanitized_metadatas.append(clean_meta)

    # Add to collection
    collection.add(
        ids=[doc["id"] for doc in documents],
        documents=[doc["text"] for doc in documents],
        metadatas=sanitized_metadatas
    )

    print(f"   ✅ Indexed {collection.count()} documents into ChromaDB")
    print(f"   💾 Persisted to: {CHROMA_PERSIST_DIR}")

    return collection


def _get_embedding_function():
    """Get the embedding function based on API key availability."""
    from chromadb.utils import embedding_functions

    if OPENAI_API_KEY and OPENAI_API_KEY != "sk-your-api-key-here":
        print(f"   🔑 Using OpenAI embeddings ({EMBEDDING_MODEL})")
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            model_name=EMBEDDING_MODEL
        )
    else:
        print("   ⚠️  No API key — using default embeddings (demo mode)")
        return embedding_functions.DefaultEmbeddingFunction()


def query_symptoms(query: str, top_k: int = 5, collection=None) -> list[dict]:
    """
    Query the knowledge base for matching ICD-10 codes.

    Args:
        query: Natural language symptom description (Turkish or English)
        top_k: Number of results to return
        collection: ChromaDB collection (loads default if None)

    Returns:
        List of dicts with: code, description, description_tr, score, type
    """
    if collection is None:
        collection = build_index()

    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )

    matches = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i] if results.get("distances") else 0
        matches.append({
            "code": meta.get("code", results["ids"][0][i]),
            "description": meta.get("description", ""),
            "description_tr": meta.get("description_tr", ""),
            "type": meta.get("type", ""),
            "dataset_mapping": meta.get("dataset_mapping"),
            "relevance_score": round(1.0 / (1.0 + distance), 4),
            "raw_distance": round(distance, 4),
        })

    return matches


def keyword_search(text: str) -> list[dict]:
    """
    Fallback keyword-based search using voice_descriptors_tr.
    Works offline without any API key.

    Args:
        text: Turkish text to search for symptom mentions

    Returns:
        List of matched ICD-10 codes with confidence scores
    """
    icd10_path = KNOWLEDGE_BASE_DIR / "icd10_lung_codes.json"
    with open(icd10_path, "r", encoding="utf-8") as f:
        icd10_data = json.load(f)

    text_lower = text.lower()
    matches = []

    # Search symptoms
    for code, info in icd10_data.get("symptoms", {}).items():
        voice_terms = info.get("voice_descriptors_tr", [])
        matched_terms = [t for t in voice_terms if t.lower() in text_lower]
        if matched_terms:
            matches.append({
                "code": code,
                "description": info["description"],
                "description_tr": info["description_tr"],
                "type": "symptom",
                "dataset_mapping": info.get("dataset_mapping"),
                "matched_terms": matched_terms,
                "relevance_score": min(1.0, len(matched_terms) * 0.5),
            })

    # Search risk factors
    for code, info in icd10_data.get("risk_factors", {}).items():
        voice_terms = info.get("voice_descriptors_tr", [])
        matched_terms = [t for t in voice_terms if t.lower() in text_lower]
        if matched_terms:
            matches.append({
                "code": code,
                "description": info["description"],
                "description_tr": info["description_tr"],
                "type": "risk_factor",
                "dataset_mapping": info.get("dataset_mapping"),
                "matched_terms": matched_terms,
                "relevance_score": min(1.0, len(matched_terms) * 0.5),
            })

    # Sort by relevance
    matches.sort(key=lambda x: x["relevance_score"], reverse=True)
    return matches


# ==============================================================
# MAIN — Test the pipeline
# ==============================================================

if __name__ == "__main__":
    print("🔍 PRAEVIDIO AI — RAG Pipeline Test")
    print("=" * 50)

    # Build index
    collection = build_index(force_rebuild=True)

    # Test queries
    test_queries = [
        "öksürük ve nefes darlığı var",
        "kan tükürme",
        "göğüs ağrısı",
        "sigara içiyorum, sürekli yorgunum",
        "kilo kaybı ve halsizlik",
    ]

    for query in test_queries:
        print(f"\n   🔎 Query: \"{query}\"")
        results = query_symptoms(query, top_k=3, collection=collection)
        for r in results:
            print(f"      → {r['code']}: {r['description_tr']} "
                  f"(score: {r['relevance_score']:.3f})")

    # Test keyword fallback
    print(f"\n{'='*50}")
    print("📝 Keyword Search Fallback Test:")
    for query in test_queries:
        print(f"\n   🔎 Query: \"{query}\"")
        results = keyword_search(query)
        for r in results:
            print(f"      → {r['code']}: {r['description_tr']} "
                  f"(matched: {r['matched_terms']})")
