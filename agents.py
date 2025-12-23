from llm_groq import groq_generate

# =====================================================
# RESEARCHER AGENT (Improved for PDF content)
# =====================================================
async def researcher_agent(query, top_k_sources=5, document_text=None):
    """
    Researcher agent for both text queries and PDF content.
    """
    context = query
    if document_text:
        # If we have document text, use it as primary content
        context = f"""
DOCUMENT CONTENT TO ANALYZE:
{document_text[:15000]}

RESEARCH TASK: {query}
"""
    
    prompt = f"""
You are a precise Researcher Agent analyzing content.

RULES (STRICT):
- Extract factual information ONLY from provided content
- Do NOT invent or hallucinate facts
- Keywords must be relevant and meaningful
- Notes should summarize key points from the content
- Be objective and factual

OUTPUT FORMAT (EXACT):

KEYWORDS:
- keyword one
- keyword two
- keyword three
- keyword four
- keyword five

NOTES:
Write clear factual notes based on the content.
Focus on key findings, data points, and important information.

CONTENT TO ANALYZE:
{context}
"""

    response = groq_generate(prompt, max_tokens=800)

    # Parse response
    keywords = []
    notes = response

    if "KEYWORDS:" in response and "NOTES:" in response:
        parts = response.split("NOTES:", 1)
        kw_block = parts[0].replace("KEYWORDS:", "").strip()
        notes = parts[1].strip()

        # Parse keywords
        for line in kw_block.splitlines():
            clean_line = line.strip().lstrip("-•* ").strip()
            if clean_line:
                keywords.append(clean_line)

    return {
        "keywords": keywords[:10],
        "notes": notes,
        "sources": ["Document analysis"] if document_text else ["Web research"]
    }

# =====================================================
# SUMMARIZER AGENT
# =====================================================
async def summarizer_agent(notes):
    prompt = f"""
You are a Summarizer Agent. Create a clear summary of the research notes.

FORMAT:

TL;DR:
(Two concise sentences summarizing the main points)

KEY POINTS:
- First key point
- Second key point  
- Third key point
- Fourth key point
- Fifth key point

RESEARCH NOTES:
{notes}
"""

    return groq_generate(prompt, max_tokens=400)

# =====================================================
# CRITIC AGENT
# =====================================================
async def critic_agent(summary):
    prompt = f"""
You are a Critic Agent. Evaluate the summary below critically.

CHECK FOR:
- Missing evidence or sources
- Logical inconsistencies  
- Unsupported claims
- Bias or assumptions
- Areas needing more information

Provide constructive criticism. Do NOT rewrite the summary.

SUMMARY TO EVALUATE:
{summary}
"""

    critique = groq_generate(prompt, max_tokens=350)
    return {"critique": critique}

# =====================================================
# WRITER AGENT
# =====================================================
async def writer_agent(summary, critique):
    prompt = f"""
You are a Writer Agent. Create a final research report using the summary and critique.

RULES:
- Use ONLY information from the summary and critique
- No new facts or information
- Professional, clear writing
- Well-structured report

REPORT STRUCTURE:
1. EXECUTIVE SUMMARY
2. KEY FINDINGS
3. ANALYSIS
4. LIMITATIONS (based on critique)
5. CONCLUSION

SUMMARY:
{summary}

CRITIQUE:
{critique['critique']}
"""

    return groq_generate(prompt, max_tokens=700)