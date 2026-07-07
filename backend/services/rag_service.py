from functools import lru_cache

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from config import settings
from services.vector_store_service import build_vector_store, get_retriever

SYSTEM_PROMPT = """You are a helpful video assistant. Answer the user's question
based ONLY on the video transcript context provided below.

If the answer is not found in the context, say:
"I could not find this information in the video transcript."
Always be concise and precise. If quoting someone, mention it clearly.

Context from video transcript:
{context}"""


@lru_cache(maxsize=1)
def get_llm():
    return ChatMistralAI(
        model="mistral-small-latest",
        mistral_api_key=settings.mistral_api_key,
        temperature=0.3,
    )


def format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def build_rag_chain(transcript: str, session_id: str):
    vector_store = build_vector_store(transcript, session_id)
    retriever = get_retriever(vector_store, k=4)
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", "{question}")]
    )

    rag_chain = (
        {
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain


def ask_question(rag_chain, question: str) -> str:
    return rag_chain.invoke(question)
