from agents import researcher_agent, summarizer_agent, critic_agent, writer_agent
from task_orchestrator import run_task_with_document

async def run_research_pipeline(
    query: str,
    top_k_sources: int = 5,
    document_text: str | None = None
):
    """
    Run the complete research pipeline for text queries.
    """
    
    # Run agents in sequence
    research = await researcher_agent(query, top_k_sources, document_text)
    summary = await summarizer_agent(research["notes"])
    critique = await critic_agent(summary)
    final_doc = await writer_agent(summary, critique)

    return {
        "keywords": research.get("keywords", []),
        "research": {
            "sources": research.get("sources", []),
            "notes": research.get("notes", ""),
            "keywords": research.get("keywords", [])
        },
        "summary": summary,
        "critique": critique,
        "final": final_doc,
        "document_analysis": document_text is not None
    }

# Re-export the task function
__all__ = ['run_research_pipeline', 'run_task_with_document']