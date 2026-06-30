from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from config import MISTRAL_API_KEY
from services.vector_store import build_vector_store, load_vector_store, get_retriever


SYSTEM_PROMPT = """You are a helpful video assistant. Answer the user's question 
based ONLY on the video transcript context provided below.

If the answer is not found in the context, say: 
"I could not find this information in the video transcript."

Always be concise and precise. If quoting someone, mention it clearly.

Context from video transcript:
{context}"""


def get_llm():
    return ChatMistralAI(
        model="mistral-small-latest",
        mistral_api_key=MISTRAL_API_KEY,
        temperature=0.3
    )


def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])


def _build_chain(retriever):
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "{question}"),
        ]
    )

    rag_chain = (
        {
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
        }
        | prompt | llm | StrOutputParser()
    )
    return rag_chain


def build_rag_chain(transcript: str, session_id: str):
    vector_store = build_vector_store(transcript, session_id)
    retriever = get_retriever(vector_store, k=4)
    return _build_chain(retriever)


def load_chain(session_id: str):
    vector_store = load_vector_store(session_id)
    retriever = get_retriever(vector_store)
    return _build_chain(retriever)


def ask_question(rag_chain, question: str) -> str:
    print(f"Question : {question}")
    answer = rag_chain.invoke(question)
    print(f"Answer : {answer}")
    return answer
