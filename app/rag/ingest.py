import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# -------------------------------------------------------
# ✅ GLOBAL CACHE (FROM V3)
# -------------------------------------------------------
_vector_store = None
FAISS_INDEX_PATH = "app/data/faiss_index"

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# -------------------------------------------------------
# ✅ BUILD VECTOR STORE (V1 BASE + V2 + V3)
# -------------------------------------------------------
def build_vector_store(file_path: str):
    global _vector_store

    # 🔥 If already loaded → reuse (V3)
    if _vector_store is not None:
        return _vector_store

    # 🔥 Load saved index (V3)
    if os.path.exists(FAISS_INDEX_PATH):
        embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
        _vector_store = FAISS.load_local(
            FAISS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
        print("[RAG] ✅ Loaded existing FAISS index")
        return _vector_store

    # 🔥 Read file (V1)
    if not os.path.exists(file_path):
        print(f"[RAG] ❌ File not found: {file_path}")
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # 🔥 Clean text (V2 improvement)
    lines = [
        line for line in raw_text.splitlines()
        if not line.strip().startswith("#") or line.strip() == ""
    ]
    text = "\n".join(lines)

    # 🔥 Improved chunking (V2)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=["\n\n", "\n", ". ", " "],
    )

    documents = splitter.create_documents([text])

    # 🔥 Embeddings (same as V1 but optimized)
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    # 🔥 Build FAISS index
    _vector_store = FAISS.from_documents(documents, embeddings)

    # 🔥 Save index (V3)
    os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
    _vector_store.save_local(FAISS_INDEX_PATH)

    print(f"[RAG] ✅ Built & saved vector store — {len(documents)} chunks")

    return _vector_store


# -------------------------------------------------------
# ✅ QUERY KNOWLEDGE (V1 BASE + V2 IMPROVEMENT)
# -------------------------------------------------------
def query_knowledge(vector_store, query: str, k: int = 3):
    if vector_store is None:
        return "Knowledge base not loaded."

    try:
        docs = vector_store.similarity_search(query, k=k)

        # 🔥 Clean output (important for LLM)
        results = [doc.page_content.strip() for doc in docs if doc.page_content]

        return "\n\n".join(results)

    except Exception as e:
        return f"Knowledge retrieval error: {str(e)}"