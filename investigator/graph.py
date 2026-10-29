
import json
from typing import TypedDict, NotRequired

from langgraph.graph import StateGraph, START, END

from investigator.evidence_bundle import build_evidence_bundle
from investigator.ai_investigator import investigate


class InvestigationState(TypedDict):
    question: str
    evidence: NotRequired[dict]
    report: NotRequired[dict]


def collect_evidence(state: InvestigationState):
    print("\n[1] Collecting incident evidence...")

    evidence = build_evidence_bundle(state["question"])

    print("    Sensor analysis completed")
    print("    Event analysis completed")
    print("    Documentation retrieval completed")

    return {"evidence": evidence}


def reason_about_incident(state: InvestigationState):
    print("\n[2] Running AI investigation...")

    report = investigate(
        question=state["question"],
        evidence=state["evidence"]
    )

    print("    AI investigation completed")

    return {"report": report}


# Construct the LangGraph workflow
builder = StateGraph(InvestigationState)

builder.add_node("collect_evidence", collect_evidence)
builder.add_node("reason_about_incident", reason_about_incident)

builder.add_edge(START, "collect_evidence")
builder.add_edge("collect_evidence", "reason_about_incident")
builder.add_edge("reason_about_incident", END)

graph = builder.compile()


if __name__ == "__main__":

    question = "Why did conveyor 2 stop around 14:20?"

    print("=== LANGGRAPH INCIDENT INVESTIGATOR ===")
    print(f"Question: {question}")

    result = graph.invoke({"question": question})

    report = result["report"]

    print("\n=== INVESTIGATION RESULT ===")
    print(json.dumps({
        "incident_summary": report["incident_summary"],
        "leading_hypothesis": report["leading_hypothesis"],
        "confidence": report["confidence"]
    }, indent=2))

    print("\nLangGraph workflow completed successfully!")
