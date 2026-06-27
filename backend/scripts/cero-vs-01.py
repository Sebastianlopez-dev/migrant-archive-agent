#!/usr/bin/env python3
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

load_dotenv()

GEMINI_CHAT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
CHROMA_COLLECTION = "migrant_archive"

TOP_K = 3
MAX_TURNS = 5

SYSTEM_PROMPT = """\
You are Cero, an assistant that answers questions in Spanish about
archived migrant testimonies. Answer the question using only the
context below. If the context does not contain enough information,
say so. Always respond in Spanish. Cite the video and timestamp
when possible.

Context:
{context}

Question: {question}

Answer:\
"""


def _ensure_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("ERROR: GEMINI_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)
    return key


_ensure_api_key()

_store = Chroma(
    collection_name=CHROMA_COLLECTION,
    embedding_function=GoogleGenerativeAIEmbeddings(model="gemini-embedding-2"),
    persist_directory=CHROMA_DIR,
)

_chain = ConversationalRetrievalChain.from_llm(
    llm=ChatGoogleGenerativeAI(model=GEMINI_CHAT_MODEL, temperature=0.2),
    retriever=_store.as_retriever(search_kwargs={"k": TOP_K}),
    memory=ConversationBufferWindowMemory(
        k=MAX_TURNS, memory_key="chat_history", return_messages=True, output_key="answer"
    ),
    return_source_documents=True,
    combine_docs_chain_kwargs={
        "prompt": PromptTemplate(
            template=SYSTEM_PROMPT,
            input_variables=["context", "question"],
        ),
    },
)


def _show_history() -> None:
    messages = _chain.memory.chat_memory.messages
    if not messages:
        print("No history yet. Try later.")
        return
    for msg in messages:
        role = "User" if msg.type == "human" else "Cero"
        print(f"[{role}] {msg.content[:80]}...")
    print(f"  ({len(messages)} mensajes, {MAX_TURNS * 2} max)")


if __name__ == "__main__":
    args = sys.argv[1:]

    if args:
        question = " ".join(args)
        try:
            result = _chain.invoke({"question": question})
        except Exception as e:
            print(f"Error: {e}. Try again later.")
            sys.exit(1)
        print(result["answer"])
    else:
        print("=" * 50)
        print("\nHi, I'm Cero \n- The Plataforma Cero's Youtube Q&A Agent.")
        print("=" * 50)
        print("\nHere some commands you can activate: \n'history' to check memory\n'q','quit','exit' to finish session.")
        print("=" * 50)
        print("\nAbove here you can insert a question for me")
        
        while True:
            try:
                question = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAdios.")
                break

            if not question:
                continue
            if question.lower() in ("q", "quit", "salir", "exit"):
                print("Adios.")
                break
            if question.lower() == "history":
                _show_history()
                continue

            try:
                result = _chain.invoke({"question": question})
            except Exception as e:
                print(f"Error: {e}. Try again later.")
                continue
            print(result["answer"])
            print()
