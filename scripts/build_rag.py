"""Rebuild the RAG vector store:  python scripts/build_rag.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag_service import RAGService  # noqa: E402


def main():
    stats = RAGService().build_index()
    print(f"RAG vector store built: {stats['documents']} documents, {stats['chunks']} chunks")
    print(f"Saved to: {stats['index_path']}")


if __name__ == "__main__":
    main()
