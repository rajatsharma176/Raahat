"""
Knowledge base ingestion script.
Run this once to build the FAISS index from the knowledge documents.

Usage:
    cd backend
    python ../scripts/ingest_knowledge.py
"""
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")

from app.rag.ingestion import ingest_knowledge_base, save_index

def main():
    print("RAAHAT Knowledge Base Ingestion")
    print("=" * 50)
    print("Loading documents from knowledge/...")

    chunks, metadata, embeddings = ingest_knowledge_base(knowledge_path="backend/knowledge")

    if not chunks:
        print("❌ No documents found. Check the knowledge/ directory.")
        return

    print(f"✅ Loaded {len(chunks)} chunks from {len(set(m['source'] for m in metadata))} documents")
    print("Building FAISS index...")

    save_index(chunks, metadata, embeddings, index_path="backend/data/faiss_index")
    print(f"✅ FAISS index built with {len(chunks)} vectors")
    print("Knowledge base ready for RAG retrieval.")


if __name__ == "__main__":
    main()
