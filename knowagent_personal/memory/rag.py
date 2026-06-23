"""Personal RAG using ChromaDB for local document search."""

import glob
import os

from knowagent_personal.config import Config


class PersonalRAG:
    """Personal document RAG with ChromaDB and local embeddings."""

    def __init__(self, config: Config):
        self.enabled = config.get("rag.enabled", False)
        self.index_path = config.get(
            "rag.index_path", os.path.expanduser("~/.knowagent/chroma")
        )
        self.embedding_model = config.get(
            "rag.embedding_model", "BAAI/bge-small-en-v1.5"
        )
        self.chunk_size = config.get("rag.chunk_size", 500)
        self.chunk_overlap = config.get("rag.chunk_overlap", 50)
        self.index_dirs = config.get("rag.index_dirs", ["~/Documents", "~/Desktop"])
        self.collection = None
        self.client = None
        self._initialized = False

    def init(self) -> bool:
        """Initialize ChromaDB collection. Returns True if successful."""
        if not self.enabled:
            return False
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            self.client = chromadb.PersistentClient(path=self.index_path)
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model
            )
            self.collection = self.client.get_or_create_collection(
                name="personal_docs",
                embedding_function=ef,
            )
            self._initialized = True
            return True
        except ImportError:
            print(
                "  ⚠ 需要安装 chromadb 和 sentence-transformers:\n"
                "    pip install chromadb sentence-transformers"
            )
            return False
        except Exception as e:
            print(f"  ⚠ RAG 初始化失败: {e}")
            return False

    def index_directory(self, path: str) -> dict:
        """Index text files in a directory. Returns stats dict."""
        if not self._initialized:
            return {"error": "RAG 未初始化", "added": 0, "skipped": 0}

        resolved = os.path.expanduser(path)
        if not os.path.exists(resolved):
            return {"error": f"目录不存在: {path}", "added": 0, "skipped": 0}

        extensions = [
            "*.txt",
            "*.md",
            "*.py",
            "*.yaml",
            "*.yml",
            "*.json",
            "*.csv",
            "*.ini",
            "*.cfg",
            "*.conf",
            "*.rst",
        ]
        files = []
        for ext in extensions:
            files.extend(glob.glob(os.path.join(resolved, "**", ext), recursive=True))

        # Limit to first 100 files for Phase 0
        files = list(dict.fromkeys(files))[:100]

        added = 0
        skipped = 0

        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if len(content.strip()) < 50:
                    skipped += 1
                    continue

                chunks = self._chunk_text(content)
                rel_path = os.path.relpath(filepath, os.path.expanduser("~"))
                ids = [f"{filepath}#{i}" for i in range(len(chunks))]
                metadatas = [
                    {"source": rel_path, "chunk": i} for i in range(len(chunks))
                ]

                self.collection.add(
                    documents=chunks,
                    ids=ids,
                    metadatas=metadatas,
                )
                added += 1
            except Exception:
                skipped += 1

        total_chunks = 0
        if hasattr(self, "collection") and self.collection:
            total_chunks = len(self.collection.get()["ids"])

        return {
            "added": added,
            "skipped": skipped,
            "total_chunks": total_chunks,
            "path": path,
        }

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        """Search indexed documents. Returns list of {content, source, score}."""
        if not self._initialized or not self.collection:
            return []
        results = self.collection.query(
            query_texts=[query], n_results=n_results
        )
        hits = []
        for i in range(len(results["ids"][0])):
            hits.append(
                {
                    "content": results["documents"][0][i][:300],
                    "source": results["metadatas"][0][i].get("source", "?"),
                    "score": (
                        results["distances"][0][i] if results.get("distances") else 0
                    ),
                }
            )
        return hits

    def _chunk_text(self, text: str) -> list[str]:
        """Simple paragraph-based chunking."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current = ""
        for p in paragraphs:
            if len(current) + len(p) < self.chunk_size:
                current += "\n\n" + p if current else p
            else:
                if current:
                    chunks.append(current)
                current = p
        if current:
            chunks.append(current)
        return chunks if chunks else [text[: self.chunk_size]]
