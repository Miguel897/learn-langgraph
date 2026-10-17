"""11 - Multi-agent: a supervisor delegating tasks to specialist sub-agents.

                 +--> weather_agent --+
    START -> supervisor               +--> supervisor -> ... -> finalize -> END
                 +--> math_agent -----+

Concepts:
  * Each specialist is a complete agent (create_agent) with its OWN tools and
    prompt, running inside a node.
  * Context isolation: the supervisor writes a focused `task` for the worker,
    and the worker sees only that task, not the whole conversation. Small
    models in particular get confused by long, multi-party histories.
  * Command(goto=..., update=...) lets a node update state AND choose the next
    node in one return value. No add_conditional_edges is needed; the
    Command[Literal[...]] return annotation tells LangGraph (and the diagram)
    which nodes are reachable.
  * A delegation limit guards against a model looping forever.
"""
from typing import Literal

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command
from pydantic import BaseModel, Field

from learn_langgraph import add, get_chat_model, get_weather, header, multiply, print_messages_stream, save_mermaid

MAX_DELEGATIONS = 4
model = get_chat_model()


class State(MessagesState):
    task: str            # current instruction for the chosen worker
    results: list[str]   # "worker: answer" lines collected so far


# --- Specialist sub-agents --------------------------------------------------
weather_agent = create_agent(
    model, [get_weather],
    system_prompt="You are a weather specialist. Use get_weather and report the result briefly.",
)
math_agent = create_agent(
    model, [add, multiply],
    system_prompt="You are a calculator. Use the add/multiply tools, then reply with the result.",
)


def make_worker(name: str, agent):
    def worker(state: State) -> Command[Literal["supervisor"]]:
        result = agent.invoke({"messages": [("user", state["task"])]})  # sees only its task
        answer = result["messages"][-1].content
        return Command(
            goto="supervisor",
            update={
                "results": state["results"] + [f"{name} (task: {state['task']}): {answer}"],
                "messages": [AIMessage(content=answer, name=name)],  # for the transcript
            },
        )
    return worker


# --- Supervisor ---------------------------------------------------------------
class Decision(BaseModel):
    next: Literal["weather_agent", "math_agent", "FINISH"] = Field(
        description="Worker for the next missing step, or FINISH when everything is answered."
    )
    task: str = Field(description="Self-contained instruction for that worker, with any numbers it needs.")


SUPERVISOR_PROMPT = (
    "You coordinate two workers:\n"
    "- weather_agent: looks up the weather of ONE city per task\n"
    "- math_agent: does arithmetic on numbers you give it\n"
    "Given the user request and the results so far, choose the worker for the next "
    "missing step and write its task. Choose FINISH only when every part is answered."
)


def briefing(state: State) -> str:
    done = "\n".join(f"- {r}" for r in state["results"]) or "- (none yet)"
    return f"User request: {state['messages'][0].content}\n\nResults so far:\n{done}"


def supervisor(state: State) -> Command[Literal["weather_agent", "math_agent", "finalize"]]:
    if len(state["results"]) >= MAX_DELEGATIONS:
        return Command(goto="finalize")
    d = model.with_structured_output(Decision).invoke(
        [("system", SUPERVISOR_PROMPT), ("human", briefing(state))]
    )
    print(f"  [supervisor -> {d.next}: {d.task}]")
    if d.next == "FINISH":
        return Command(goto="finalize")
    return Command(goto=d.next, update={"task": d.task})


def finalize(state: State) -> dict:
    reply = model.invoke(
        f"{briefing(state)}\n\nAnswer the user request in 1-2 sentences using these results."
    )
    return {"messages": [AIMessage(content=reply.content, name="supervisor")]}


builder = StateGraph(State)
builder.add_node("supervisor", supervisor)
builder.add_node("weather_agent", make_worker("weather_agent", weather_agent))
builder.add_node("math_agent", make_worker("math_agent", math_agent))
builder.add_node("finalize", finalize)
builder.add_edge(START, "supervisor")
builder.add_edge("finalize", END)

graph = builder.compile()
save_mermaid(graph, "11_supervisor")

question = "What's the temperature in Madrid and in London, and what is their product?"
header(question)
print_messages_stream(graph, {"messages": [("user", question)], "results": []})
