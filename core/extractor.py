# Actionable items, decisions, questions

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os


def get_llm():
    return ChatMistralAI(model="mistral-small-latest", mistral_api_key=os.getenv("MISTRAL_API_KEY"), temperature=0.2)


def split_transcript(transcript: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=200,
    )
    return splitter.split_text(transcript)


def build_chain(system_prompt: str):
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{text}"),
        ]
    )
    return (
        RunnablePassthrough()
        | RunnableLambda(lambda x: {"text": x})
        | prompt
        | llm
        | StrOutputParser()
    )


def _extract_with_chunking(transcript: str, map_prompt: str, combine_prompt: str) -> str:
    """
    Map-reduce extraction for long transcripts.
    1. Split transcript into chunks (same chunking as summarizer.py).
    2. Run the extraction prompt on each chunk (map).
    3. Merge/dedupe the partial results into one clean final list (reduce).
    """
    chunks = split_transcript(transcript)

    # If transcript is short enough to fit in one chunk, skip the merge step entirely.
    if len(chunks) == 1:
        chain = build_chain(map_prompt)
        return chain.invoke(chunks[0])

    map_chain = build_chain(map_prompt)
    partial_results = [map_chain.invoke(chunk) for chunk in chunks]

    combined = "\n\n".join(
        f"--- Chunk {i+1} ---\n{result}" for i, result in enumerate(partial_results)
    )

    combine_chain = build_chain(combine_prompt)
    return combine_chain.invoke(combined)


def extract_action_items(transcript: str) -> str:
    """
    Despite the name (kept for backward compatibility with main.py/app.py),
    this extracts general "Takeaways & Recommendations" suitable for any
    video -- commentary, tutorials, podcasts -- not just meetings.
    """
    map_prompt = (
        "You are analyzing a portion of a video transcript (this could be commentary, "
        "a tutorial, a podcast, or any spoken content). From this portion, extract "
        "practical takeaways or recommendations -- concrete advice, steps, or actions "
        "the speaker suggests a viewer could take or learn from. "
        "Format as a numbered list. If none found in this portion, say "
        "'No takeaways found in this portion.'"
    )
    combine_prompt = (
        "Below are takeaways and recommendations extracted from different portions "
        "of the same video transcript, in order. Merge them into one single, "
        "deduplicated, clean numbered list of practical takeaways. "
        "Combine duplicate or related points across portions into a single entry. "
        "Ignore any 'No takeaways found' notes. If the final list is empty, say "
        "'No clear takeaways or recommendations found.'"
    )
    return _extract_with_chunking(transcript, map_prompt, combine_prompt)


def extract_key_decisions(transcript: str) -> str:
    """
    Despite the name (kept for backward compatibility with main.py/app.py),
    this extracts "Key Claims & Conclusions" -- definitive statements,
    opinions, or conclusions the speaker makes -- suitable for commentary,
    tutorials, podcasts, or any general video content.
    """
    map_prompt = (
        "You are analyzing a portion of a video transcript. From this portion, "
        "extract the key claims or conclusions the speaker makes -- definitive "
        "statements, strong opinions, or conclusions they assert as true. "
        "Format as a numbered list. If none found in this portion, say "
        "'No key claims found in this portion.'"
    )
    combine_prompt = (
        "Below are key claims and conclusions extracted from different portions "
        "of the same video transcript, in order. Merge them into one single, "
        "deduplicated, clean numbered list of the speaker's key claims. "
        "Combine duplicate or related claims across portions into a single entry. "
        "Ignore any 'No key claims found' notes. If the final list is empty, say "
        "'No clear key claims or conclusions found.'"
    )
    return _extract_with_chunking(transcript, map_prompt, combine_prompt)


def extract_questions(transcript: str) -> str:
    map_prompt = (
        "You are analyzing a portion of a video transcript. From this portion, "
        "extract unresolved questions, open-ended points, or topics the speaker "
        "raises but doesn't fully answer or resolve. "
        "Format as a numbered list. If none found in this portion, say "
        "'No open questions found in this portion.'"
    )
    combine_prompt = (
        "Below are open questions and unresolved points extracted from different "
        "portions of the same video transcript, in order. Merge them into one "
        "single, deduplicated, clean numbered list. "
        "Ignore any 'No open questions found' notes. If the final list is empty, say "
        "'No open questions found.'"
    )
    return _extract_with_chunking(transcript, map_prompt, combine_prompt)