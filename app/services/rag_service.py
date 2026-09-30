"""A small but REAL Retrieval-Augmented Generation (RAG) pipeline.

    Documents -> Loading -> Chunking -> Embeddings -> Vector store
        -> Similarity search -> Top-K context -> (LLM) -> Grounded answer

Design choices (kept simple on purpose):
* Embeddings: TF-IDF style hashed vectors (unigrams + bigrams) created locally.
  No model download, no API key and no internet are needed, so RAG works on any
  Windows machine and can be unit-tested. The design is the same as a neural
  embedding: text -> vector -> cosine similarity.
* Vector store: one JSON file (data/vector_store/index.json) with sparse vectors.
  ChromaDB was not used because it downloads an embedding model on first use,
  which is fragile on university/Windows networks.
"""
import hashlib
import json
import logging
import math
import re
from collections import Counter
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

DIMENSIONS = 4096
STOPWORDS = set("""a an the and or of to in on for with is are was were be been it this that these those as at by from
how what which who do does can i my me you your we our should would could about into than then so if not no
get make use need want tell help improve become best way next good new please
""".split())

NO_CONTEXT_MESSAGE = "The available knowledge base does not contain enough information to answer this question."


# ---------------------------------------------------------------- 1. loading
def load_documents(kb_dir: Optional[Path] = None) -> list:
    """Read every .md/.txt file (and learning-resource .json records) from the knowledge base."""
    kb_dir = Path(kb_dir or settings.KNOWLEDGE_BASE_DIR)
    documents = []
    for path in sorted(kb_dir.rglob("*")):
        if not path.is_file():
            continue
        category = path.parent.name
        source = path.relative_to(kb_dir).as_posix()
        if path.suffix.lower() in (".md", ".txt"):
            raw = path.read_text(encoding="utf-8").strip()
            first, _, rest = raw.partition("\n")
            title = first.lstrip("# ").strip() if first.startswith("#") else path.stem.replace("_", " ").title()
            body = rest.strip() if first.startswith("#") else raw
            documents.append({"title": title, "category": category, "source": source, "text": body})
        elif path.suffix.lower() == ".json":
            try:
                records = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.error("Invalid JSON in knowledge base file %s", path)
                continue
            for rec in records:
                title = f"{rec.get('title', 'Resource')} ({rec.get('type', 'resource')})"
                text = (f"Type: {rec.get('type', '')}. Skill: {rec.get('skill', '')}. "
                        f"{rec.get('description', '')} Link: {rec.get('url', '')}")
                documents.append({"title": title, "category": category, "source": source, "text": text})
    return documents


# ---------------------------------------------------------------- 2. chunking
def chunk_text(text: str, max_words: int = 110, overlap_words: int = 20) -> list:
    """Split text into line-based chunks of ~max_words words with a small overlap."""
    lines = [line for line in text.splitlines() if line.strip()]
    chunks, current, count = [], [], 0
    for line in lines:
        words = len(line.split())
        if current and count + words > max_words:
            chunks.append("\n".join(current))
            keep, kept = [], 0
            for previous in reversed(current):
                w = len(previous.split())
                if kept + w > overlap_words:
                    break
                keep.insert(0, previous)
                kept += w
            current, count = keep, kept
        current.append(line)
        count += words
    if current:
        chunks.append("\n".join(current))
    return chunks


# ---------------------------------------------------------------- 3. embeddings
def _stem(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> list:
    tokens = re.findall(r"[a-z0-9]+(?:[+#]+)?", text.lower())
    return [_stem(t) for t in tokens if t not in STOPWORDS and len(t) > 1]


def _bucket(term: str) -> int:
    return int(hashlib.md5(term.encode("utf-8")).hexdigest()[:8], 16) % DIMENSIONS


MIN_COVERAGE = 0.5    # at least half of the question's words must occur in a retrieved chunk
BIGRAM_WEIGHT = 0.5   # word pairs count half as much as single words


def term_counts(text: str) -> tuple:
    """Return (unigram counts, bigram counts) as hashed-bucket Counters."""
    tokens = tokenize(text)
    unigrams = Counter(_bucket(t) for t in tokens)
    bigrams = Counter(_bucket(a + "_" + b) for a, b in zip(tokens, tokens[1:]))
    return unigrams, bigrams


def embed(text: str, idf: dict, default_idf: float) -> dict:
    """Return a sparse, L2-normalised TF-IDF vector {bucket: weight}."""
    unigrams, bigrams = term_counts(text)
    weights = {}
    for counts, factor in ((unigrams, 1.0), (bigrams, BIGRAM_WEIGHT)):
        for bucket, count in counts.items():
            weights[bucket] = weights.get(bucket, 0.0) + factor * (1 + math.log(count)) * idf.get(bucket, default_idf)
    norm = math.sqrt(sum(w * w for w in weights.values())) or 1.0
    return {b: w / norm for b, w in weights.items()}


def cosine(query_vec: dict, chunk_vec: dict) -> float:
    if len(query_vec) > len(chunk_vec):
        query_vec, chunk_vec = chunk_vec, query_vec
    return sum(w * chunk_vec.get(b, 0.0) for b, w in query_vec.items())


def _embedding_text(chunk: dict) -> str:
    """The title is repeated so that document titles weigh more than body words."""
    return f"{chunk['title']}. {chunk['title']}. {chunk['title']}. {chunk['text']}"


# ---------------------------------------------------------------- 4. vector store + retrieval
class RAGService:
    def __init__(self, kb_dir: Optional[Path] = None, index_path: Optional[Path] = None):
        self.kb_dir = Path(kb_dir or settings.KNOWLEDGE_BASE_DIR)
        self.index_path = Path(index_path or settings.VECTOR_STORE_PATH)
        self._index = None

    # ---- indexing
    def build_index(self) -> dict:
        """(Re)build the vector store from the knowledge-base folder."""
        documents = load_documents(self.kb_dir)
        chunks = []
        for doc in documents:
            for number, piece in enumerate(chunk_text(doc["text"])):
                chunks.append({
                    "id": f"{doc['source']}#{number}", "title": doc["title"], "category": doc["category"],
                    "source": doc["source"], "text": piece,
                })
        doc_freq = Counter()
        for chunk in chunks:
            uni, bi = term_counts(_embedding_text(chunk))
            doc_freq.update(uni.keys())
            doc_freq.update(bi.keys())
        total = len(chunks)
        idf = {b: math.log((total + 1) / (df + 1)) + 1 for b, df in doc_freq.items()}
        default_idf = math.log(total + 1) + 1
        for chunk in chunks:
            chunk["vector"] = embed(_embedding_text(chunk), idf, default_idf)
        self._index = {"idf": idf, "default_idf": default_idf, "chunks": chunks}
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(self._index), encoding="utf-8")
        logger.info("RAG index built: %d documents, %d chunks", len(documents), total)
        return {"documents": len(documents), "chunks": total, "index_path": str(self.index_path)}

    def _load_index(self) -> dict:
        if self._index is None:
            if not self.index_path.exists():
                self.build_index()
            else:
                raw = json.loads(self.index_path.read_text(encoding="utf-8"))
                raw["idf"] = {int(b): w for b, w in raw["idf"].items()}
                for chunk in raw["chunks"]:
                    chunk["vector"] = {int(b): w for b, w in chunk["vector"].items()}
                self._index = raw
        return self._index

    def status(self) -> dict:
        try:
            index = self._load_index()
            return {"ready": True, "chunks": len(index["chunks"])}
        except Exception as exc:  # never crash the API because of the index
            logger.error("RAG index unavailable: %s", exc)
            return {"ready": False, "chunks": 0}

    # ---- retrieval
    def retrieve(self, query: str, top_k: Optional[int] = None, category: Optional[str] = None,
                 min_score: Optional[float] = None) -> list:
        """Top-K similarity search. Returns [] when nothing is relevant enough."""
        top_k = top_k or settings.RAG_TOP_K
        min_score = settings.RAG_MIN_SCORE if min_score is None else min_score
        index = self._load_index()
        query_vec = embed(query, index["idf"], index["default_idf"])
        query_terms = set(term_counts(query)[0])
        if not query_terms:
            return []
        scored = []
        for chunk in index["chunks"]:
            if category and chunk["category"] != category:
                continue
            score = cosine(query_vec, chunk["vector"])
            # Coverage: how many of the question's words appear in the chunk (blocks off-topic matches).
            coverage = sum(1 for b in query_terms if b in chunk["vector"]) / len(query_terms)
            if score >= min_score and coverage >= MIN_COVERAGE:
                scored.append((score, chunk))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [{"id": c["id"], "title": c["title"], "category": c["category"], "source": c["source"],
                 "text": c["text"], "score": round(s, 3)} for s, c in scored[:top_k]]

    @staticmethod
    def format_context(chunks: list) -> str:
        """Text block injected into the LLM prompt."""
        return "\n\n".join(f"[{i}] ({c['category']} / {c['title']})\n{c['text']}" for i, c in enumerate(chunks, 1))


rag_service = RAGService()
