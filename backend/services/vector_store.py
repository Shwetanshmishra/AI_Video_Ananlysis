from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config import CHROMA_DIR

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceBgeEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
        )
    return _embeddings


def _collection_name(session_id: str) -> str:
    # Namespaced per session so concurrent API requests don't overwrite
    # each other's transcript embeddings (the original single-user script
    # used one fixed collection name — that no longer works once this runs
    # behind a multi-request FastAPI server).
    return f"meeting-transcript-{session_id}"


def build_vector_store(transcript: str, session_id: str) -> Chroma:
    print(f"Building vector store for session {session_id}")

    embeddings = get_embeddings()
    collection_name = _collection_name(session_id)

    # Clear any pre-existing collection for this session id
    try:
        old = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR,
        )
        old.delete_collection()
        print("Cleared previous vector store collection for this session")
    except Exception:
        pass  # Nothing to clear on first run

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = splitter.split_text(transcript)
    print(f"Split transcript into {len(chunks)} chunks")

    docs = [
        Document(page_content=chunk, metadata={"chunk_index": i})
        for i, chunk in enumerate(chunks)
    ]

    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=CHROMA_DIR,
    )

    return vector_store


def load_vector_store(session_id: str) -> Chroma:
    embeddings = get_embeddings()
    return Chroma(
        collection_name=_collection_name(session_id),
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )


def get_retriever(vector_store: Chroma, k: int = 6):
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )
