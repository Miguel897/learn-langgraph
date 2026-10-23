"""13 - Evaluating an agent: a small dataset, code checks and an LLM judge.

    dataset --> agent --> run (answer + tool trajectory)
                              |
              +---------------+----------------+
              v               v                v
        tools_used      answer_contains    llm_judge
        (code check)     (code check)    (model grades)
              +---------------+----------------+
                              v
          scores per case + pass rates  --(keys set?)-->  Langfuse trace + scores
                              v
          pass rate >= MIN_PASS_RATE ?  exit 0 : exit 1   (CI regression gate)

Concepts:
  * Eval dataset: inputs plus what "good" looks like (expected tools,
    a reference answer). Version it like code and grow it from real failures.
  * Trajectory eval: inspect the AIMessage.tool_calls in the final state, not
    just the answer. The right answer with the wrong tools is a lucky guess.
  * Deterministic evaluators: cheap, exact, run them first.
  * LLM-as-judge: a model with structured output grades fuzzy criteria.
    Judges are noisy (especially small ones); keep the rubric short and binary.
  * What to notice: the small model often adds 14 + 22 "in its head". The answer
    is right, the judge passes it, and only the trajectory check fails.
  * Observability: with LANGFUSE_* keys set, each case becomes a Langfuse
    trace (every model and tool call inside it) with the three scores
    attached, so you can open a failing case and see exactly what happened.
  * Regression gate: a non-zero exit code when quality drops fails CI.
"""
import sys
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from learn_langgraph import BASIC_TOOLS, get_chat_model, header, langfuse_enabled, tracing_config

MIN_PASS_RATE = 0.75  # over all checks; the small model is not perfect

agent =create_agent(
    model=get_chat_model(),
    tools=BASIC_TOOLS,
    system_prompt="Always use tools for weather and maths. Answer in one short sentence.",
)


@dataclass
class Case:
    question: str
    expected_tools: set[str]
    must_contain: str  # substring the final answer must include ("" = no check)
    reference: str  # what a correct answer says, for the judge


DATASET = [
    Case("What's the weather in Madrid?", {"get_weather"}, "28", "It is 28°C and sunny in Madrid."),
    Case("What is 12 times 7?", {"multiply"}, "84", "12 times 7 is 84."),
    Case(
        "Add the temperatures of London and Tokyo.",
        {"get_weather", "add"},
        "36",
        "London is 14°C and Tokyo 22°C; together 36.",
    ),
    Case("Hi! What can you help me with?", set(), "", "A friendly greeting offering help with weather or maths."),
]


# --- evaluators: each returns (passed, comment) -----------------------------
def tools_used(case: Case, run: dict) -> tuple[bool, str]:
    called = {c["name"] for m in run["messages"] if isinstance(m, AIMessage) for c in m.tool_calls}
    return called == case.expected_tools, f"called {sorted(called)}"


def answer_contains(case: Case, run: dict) -> tuple[bool, str]:
    answer = run["messages"][-1].text
    return case.must_contain in answer, repr(answer[:60])


class Grade(BaseModel):
    reasoning: str = Field(description="One sentence comparing the answer with the reference.")
    correct: bool = Field(description="True if the answer agrees with the reference.")


judge = get_chat_model().with_structured_output(Grade)


def llm_judge(case: Case, run: dict) -> tuple[bool, str]:
    grade = judge.invoke(
        "Grade the answer against the reference. Ignore wording, check the facts.\n"
        f"Question: {case.question}\nReference: {case.reference}\nAnswer: {run['messages'][-1].text}"
    )
    return grade.correct, grade.reasoning


EVALUATORS = [tools_used, answer_contains, llm_judge]

if __name__ == "__main__":
    langfuse = None
    if langfuse_enabled():
        from langfuse import get_client

        langfuse = get_client()
    header(f"Running the dataset (Langfuse tracing {'on' if langfuse else 'off'})")

    scores: dict[str, list[bool]] = {e.__name__: [] for e in EVALUATORS}
    for case in DATASET:
        trace_id = langfuse.create_trace_id() if langfuse else None
        run = agent.invoke({"messages": [("user", case.question)]}, tracing_config(trace_id))
        print(f"\nQ: {case.question}")
        for evaluator in EVALUATORS:
            passed, comment = evaluator(case, run)
            scores[evaluator.__name__].append(passed)
            print(f"  {'PASS' if passed else 'FAIL'}  {evaluator.__name__:<16} {comment[:90]}")
            if langfuse:
                langfuse.create_score(
                    name=evaluator.__name__, value=float(passed), data_type="BOOLEAN", trace_id=trace_id, comment=comment
                )

    header("Summary")
    for name, results in scores.items():
        print(f"  {name:<16} {sum(results)}/{len(results)} passed")
    all_checks = [s for results in scores.values() for s in results]
    pass_rate = sum(all_checks) / len(all_checks)
    print(f"\n  overall pass rate {pass_rate:.0%} (gate: {MIN_PASS_RATE:.0%})")
    if langfuse:
        langfuse.flush()  # spans are sent in the background; don't lose them on exit
    if pass_rate < MIN_PASS_RATE:
        sys.exit("FAILED: pass rate below the gate")
