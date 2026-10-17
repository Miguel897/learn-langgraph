"""01 - LangChain chat model basics (no graph yet).

Concepts:
  * Chat models take a list of messages and return an AIMessage.
  * Message types: SystemMessage, HumanMessage, AIMessage (and ToolMessage, see 02).
  * .invoke() vs .stream()
  * Runnables compose with `|` (LCEL): prompt | model | parser
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from learn_langgraph import get_chat_model, header

model = get_chat_model(temperature=0.3)

header("1. invoke() with a list of messages")
reply = model.invoke(
    [
        SystemMessage("You are a terse assistant. Answer in one sentence."),
        HumanMessage("What is LangGraph?"),
    ]
)
print(type(reply).__name__, "->", reply.content)

header("2. stream() token by token")
for chunk in model.stream("Count from 1 to 10, comma separated."):
    print(chunk.content, end="", flush=True)
print()

header("3. Prompt template | model | parser  (a Runnable chain)")
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You explain {topic} to a {audience}. Max 2 sentences."),
        ("human", "{question}"),
    ]
)
chain = prompt | model | StrOutputParser()
print(chain.invoke({"topic": "graphs", "audience": "10-year-old", "question": "What is a node?"}))

header("4. batch() runs several inputs concurrently")
answers = chain.batch(
    [
        {"topic": "Python", "audience": "chef", "question": "What is a function?"},
        {"topic": "Python", "audience": "pilot", "question": "What is a loop?"},
    ]
)
for a in answers:
    print("-", a)
