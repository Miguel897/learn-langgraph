"""08 - Agentic RAG: the agent decides when to search a knowledge base.

Concepts:
  * Embeddings + vector store (InMemoryVectorStore, local Ollama embeddings).
  * Text splitting into chunks, indexing, similarity search.
  * Exposing the retriever as a tool, so the agent loop from 05/06 can use it.
"""
from langchain.agents import create_agent
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore

from learn_langgraph import get_chat_model, get_embeddings, header, print_messages_stream

# A tiny "knowledge base" about a fictional company.
NOTES = [
    "Acme Robotics was founded in 2019 in Valencia, Spain by Lucia Ortega.",
    "Acme's flagship product is the R2 vacuum robot, priced at 499 EUR.",
    "The R2 battery lasts 140 minutes and recharges in 3 hours.",
    "Acme offers a 3-year warranty on all robots purchased after January 2024.",
    "Support is available Monday to Friday, 9:00-18:00 CET, at support@acme.example.",
    "The R3 model, announced for 2027, adds mopping and stair detection.",
]

header("Indexing documents")
store = InMemoryVectorStore(get_embeddings())
store.add_documents([Document(page_content=t, metadata={"id": i}) for i, t in enumerate(NOTES)])
print(f"{len(NOTES)} chunks indexed")


@tool
def search_knowledge_base(query: str) -> str:
    """Search Acme Robotics' internal documentation. Use for any question about Acme."""
    docs = store.similarity_search(query, k=3)
    return "\n".join(f"- {d.page_content}" for d in docs)


agent = create_agent(
    model=get_chat_model(),
    tools=[search_knowledge_base],
    system_prompt=(
        "You answer questions about Acme Robotics. ALWAYS call search_knowledge_base "
        "first, then answer only from what it returns. If the results don't contain "
        "the answer, say you don't know."
    ),
)

for q in ["How long does the R2 battery last and what does it cost?",
          "Who is the CEO of Acme?"]:
    header(q)
    print_messages_stream(agent, {"messages": [("user", q)]})
