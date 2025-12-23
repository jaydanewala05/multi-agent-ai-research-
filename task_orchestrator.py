"""
Task Orchestrator - Routes tasks to specialized agents
"""
from llm_groq import groq_generate

class TaskRouter:
    """Routes tasks to appropriate handlers"""
    
    @staticmethod
    def identify_task_type(task: str) -> str:
        """Identify what type of task the user wants"""
        
        task_lower = task.lower()
        
        if any(keyword in task_lower for keyword in [
            "keyword", "extract keyword", "list keyword", "find keyword"
        ]):
            return "keyword_extraction"
        
        elif any(keyword in task_lower for keyword in [
            "summarize", "summary", "main points", "brief", "overview"
        ]):
            return "summarization"
        
        elif any(keyword in task_lower for keyword in [
            "date", "timeline", "when", "year", "schedule"
        ]):
            return "date_extraction"
        
        elif any(keyword in task_lower for keyword in [
            "recommend", "suggest", "advice", "proposal"
        ]):
            return "recommendation_extraction"
        
        elif any(keyword in task_lower for keyword in [
            "analyze", "analysis", "evaluate", "assess", "review"
        ]):
            return "analysis"
        
        elif any(keyword in task_lower for keyword in [
            "find", "extract", "list", "identify", "locate"
        ]):
            return "information_extraction"
        
        else:
            return "general_analysis"

class TaskExecutor:
    """Executes specific types of tasks"""
    
    @staticmethod
    async def execute_keyword_extraction(document_text: str, task: str) -> dict:
        """Extract keywords from document"""
        prompt = f"""
        TASK: {task}
        
        DOCUMENT CONTENT:
        {document_text[:8000]}
        
        Extract relevant keywords from the document. Focus on:
        1. Technical terms
        2. Important concepts
        3. Key entities
        4. Main topics
        
        Format your response as:
        
        KEYWORDS:
        - keyword1
        - keyword2
        - keyword3
        ...
        
        ANALYSIS:
        [Brief analysis of why these keywords are important]
        """
        
        response = groq_generate(prompt, max_tokens=500)
        
        # Parse response
        keywords = []
        analysis = ""
        
        if "KEYWORDS:" in response and "ANALYSIS:" in response:
            parts = response.split("ANALYSIS:", 1)
            kw_block = parts[0].replace("KEYWORDS:", "").strip()
            analysis = parts[1].strip()
            
            for line in kw_block.splitlines():
                clean_line = line.strip().lstrip("-•* ").strip()
                if clean_line:
                    keywords.append(clean_line)
        else:
            analysis = response
        
        return {
            "task_type": "keyword_extraction",
            "keywords": keywords[:20],
            "analysis": analysis,
            "keyword_count": len(keywords)
        }
    
    @staticmethod
    async def execute_summarization(document_text: str, task: str) -> dict:
        """Create summary of document"""
        prompt = f"""
        TASK: {task}
        
        DOCUMENT CONTENT:
        {document_text[:10000]}
        
        Create a comprehensive summary. Include:
        1. Main topic/thesis
        2. Key arguments/points
        3. Important findings
        4. Conclusions
        
        Format your response as:
        
        EXECUTIVE SUMMARY:
        [2-3 paragraph high-level summary]
        
        DETAILED SUMMARY:
        [More detailed summary with specific points]
        
        KEY TAKEAWAYS:
        - Takeaway 1
        - Takeaway 2
        - Takeaway 3
        ...
        """
        
        response = groq_generate(prompt, max_tokens=700)
        
        return {
            "task_type": "summarization",
            "response": response,
            "summary_length": len(response)
        }
    
    @staticmethod
    async def execute_date_extraction(document_text: str, task: str) -> dict:
        """Extract dates and timeline from document"""
        prompt = f"""
        TASK: {task}
        
        DOCUMENT CONTENT:
        {document_text[:8000]}
        
        Extract all dates, timelines, and temporal information. Include:
        1. Specific dates (YYYY-MM-DD)
        2. Years mentioned
        3. Time periods
        4. Deadlines
        5. Schedules
        
        Format your response as:
        
        TIMELINE:
        - Date/Year: Event/Description
        - Date/Year: Event/Description
        ...
        
        DATE ANALYSIS:
        [Analysis of the timeline and its significance]
        
        KEY DATES:
        - Most important date 1: Reason
        - Most important date 2: Reason
        ...
        """
        
        response = groq_generate(prompt, max_tokens=600)
        
        return {
            "task_type": "date_extraction",
            "response": response,
            "contains_timeline": "TIMELINE:" in response
        }
    
    @staticmethod
    async def execute_recommendation_extraction(document_text: str, task: str) -> dict:
        """Extract recommendations from document"""
        prompt = f"""
        TASK: {task}
        
        DOCUMENT CONTENT:
        {document_text[:8000]}
        
        Extract all recommendations, suggestions, proposals, or advice from the document.
        
        Format your response as:
        
        RECOMMENDATIONS:
        - Recommendation 1 (with context)
        - Recommendation 2 (with context)
        ...
        
        PRIORITY LEVEL:
        [Indicate which recommendations are most important]
        
        IMPLEMENTATION NOTES:
        [Notes on how to implement these recommendations]
        """
        
        response = groq_generate(prompt, max_tokens=600)
        
        return {
            "task_type": "recommendation_extraction",
            "response": response,
            "recommendation_count": response.count("- Recommendation")
        }
    
    @staticmethod
    async def execute_general_analysis(document_text: str, task: str) -> dict:
        """General document analysis"""
        prompt = f"""
        TASK: {task}
        
        DOCUMENT CONTENT:
        {document_text[:12000]}
        
        Perform a comprehensive analysis of the document based on the user's task.
        
        Format your response as:
        
        TASK ANALYSIS:
        [How you approached the task]
        
        FINDINGS:
        - Finding 1
        - Finding 2
        - Finding 3
        ...
        
        INSIGHTS:
        [Key insights from your analysis]
        
        NEXT STEPS:
        [Suggested next actions based on analysis]
        """
        
        response = groq_generate(prompt, max_tokens=800)
        
        return {
            "task_type": "general_analysis",
            "response": response,
            "analysis_complete": True
        }

async def run_task_with_document(task: str, document_text: str, top_k_sources: int = 3) -> dict:
    """Main function to execute tasks with documents"""
    
    # Identify task type
    task_type = TaskRouter.identify_task_type(task)
    
    # Execute based on task type
    executor = TaskExecutor()
    
    if task_type == "keyword_extraction":
        result = await executor.execute_keyword_extraction(document_text, task)
    
    elif task_type == "summarization":
        result = await executor.execute_summarization(document_text, task)
    
    elif task_type == "date_extraction":
        result = await executor.execute_date_extraction(document_text, task)
    
    elif task_type == "recommendation_extraction":
        result = await executor.execute_recommendation_extraction(document_text, task)
    
    elif task_type == "information_extraction":
        # Use general analysis for information extraction
        result = await executor.execute_general_analysis(document_text, task)
    
    else:
        result = await executor.execute_general_analysis(document_text, task)
    
    # Add metadata
    result.update({
        "user_task": task,
        "task_type": task_type,
        "document_length": len(document_text),
        "processed_chars": min(len(document_text), 12000),
        "execution_timestamp": datetime.now().isoformat()
    })
    
    return result

from datetime import datetime