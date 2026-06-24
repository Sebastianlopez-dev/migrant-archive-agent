 ConversationBufferMemory → RunnableWithMessageHistory
Fuente oficial: LangChain Migration Guide — ConversationBufferMemory (https://python.langchain.com/docs/versions/migrating_memory/conversation_buffer_memory/)
La documentación oficial de LangChain dice explícitamente que ConversationBufferMemory está deprecated y muestra el reemplazo directo:
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

store = {}
def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

chain = RunnableWithMessageHistory(agent, get_session_history, ...)
Fuente de respaldo: Aurelio AI — Conversational Memory in LangChain (https://www.aurelio.ai/learn/langchain-conversational-memory) que explica el paso a paso de la migración con ejemplos de código.


README:


## Architecture Decisions

### Native Tool Calling over ReAct Text Parsing
Gemini 2.5 Flash supports native function calling via structured tool messages.
Using `create_tool_calling_agent` eliminates the text-parsing failures that
plagued the previous ReAct implementation.  
→ [LangChain + Gemini Function Calling Guide](https://www.philschmid.de/gemini-function-calling)

### Message History over ConversationBufferMemory
`ConversationBufferMemory` was deprecated in LangChain 0.3.1. Migrated to
`RunnableWithMessageHistory` + `InMemoryChatMessageHistory` per official guidance.  
→ [LangChain Memory Migration Guide](https://python.langchain.com/docs/versions/migrating_memory/conversation_buffer_memory/)