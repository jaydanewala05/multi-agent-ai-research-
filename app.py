from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import tempfile
import os
import fitz  # PyMuPDF
import json
import uuid
from datetime import datetime
import base64
import io
from PIL import Image
import requests

from orchestrator import run_research_pipeline, run_task_with_document
from db import init_db, save_history, get_history, save_task_result
from llm_groq import groq_generate
from ocr_utils import extract_text_from_image, analyze_image_content  # NEW IMPORT

# --------------------------------------------------------
# Create FastAPI App
# --------------------------------------------------------
app = FastAPI(title="AI Agent Task Execution System")

# Initialize SQLite DB
try:
    init_db()
except Exception as e:
    print(f"DB init note: {e}")

# --------------------------------------------------------
# CORS (Dev Mode)
# --------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------
# Request Models
# --------------------------------------------------------
class ResearchRequest(BaseModel):
    query: str
    top_k_sources: int = 3

class ChatRequest(BaseModel):
    message: str
    max_tokens: int = 300

class ImageAnalysisRequest(BaseModel):
    task: str = "Describe this image"
    max_tokens: int = 500

# --------------------------------------------------------
# Task Queue
# --------------------------------------------------------
task_queue = {}
task_results = {}

# --------------------------------------------------------
# PDF Text Extraction Function
# --------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using PyMuPDF"""
    try:
        text = ""
        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc, start=1):
                page_text = page.get_text().strip()
                if page_text:
                    text += f"\n\n[PAGE {page_num}]\n{page_text}"
        return text.strip()
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""

# --------------------------------------------------------
# Image Analysis Functions - UPDATED WITH REAL OCR
# --------------------------------------------------------
def encode_image_to_base64(image_path: str) -> str:
    """Encode image to base64"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Image encoding error: {e}")
        return ""

async def analyze_image_with_llm_and_ocr(image_path: str, task: str = "Describe this image", max_tokens: int = 500) -> Dict[str, Any]:
    """Analyze image using OCR and LLM"""
    
    try:
        # First, extract text from image using OCR
        ocr_text = extract_text_from_image(image_path)
        
        # Get image analysis
        image_analysis = analyze_image_content(image_path)
        
        # Prepare prompt based on user task
        if "text" in task.lower() or "copy" in task.lower() or "read" in task.lower() or "extract" in task.lower():
            # User wants text extraction
            if ocr_text:
                prompt = f"""
USER TASK: {task}

IMAGE TEXT EXTRACTED USING OCR:
{ocr_text}

Please analyze the extracted text and respond to the user's query: "{task}"

Provide:
1. The extracted text clearly formatted
2. Any analysis or insights about the text
3. Accuracy assessment of the OCR extraction
4. Any additional context from the text

RESPONSE:"""
            else:
                prompt = f"""
USER TASK: {task}

OCR ANALYSIS: No text was found in the image.

IMAGE INFO: {image_analysis.get('image_info', {})}

Please respond to the user's query: "{task}"

Explain that no text was detected in the image and provide suggestions for better image quality if text extraction was expected.

RESPONSE:"""
        else:
            # General image analysis
            prompt = f"""
USER TASK: {task}

IMAGE INFORMATION:
- Size: {image_analysis.get('image_info', {}).get('size', 'Unknown')}
- Format: {image_analysis.get('image_info', {}).get('format', 'Unknown')}
- Contains text: {image_analysis.get('contains_text', False)}
- Text length if any: {image_analysis.get('text_length', 0)} characters

EXTRACTED TEXT (if any):
{ocr_text if ocr_text else "No text detected"}

Analyze this image based on the user's query: "{task}"

Provide a comprehensive analysis including:
1. Description of what the image likely contains
2. Analysis of any extracted text
3. Context and insights
4. Response to the specific query

RESPONSE:"""
        
        # Generate response
        response = groq_generate(prompt, max_tokens=max_tokens)
        
        return {
            "analysis": response,
            "extracted_text": ocr_text,
            "ocr_success": bool(ocr_text),
            "image_analysis": image_analysis,
            "task": task,
            "user_query": task,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Image analysis error: {e}")
        return {
            "error": str(e),
            "fallback_response": f"Image analysis failed. User query was: '{task}'",
            "user_query": task
        }

def get_image_metadata(image_path: str) -> Dict[str, Any]:
    """Extract basic image metadata"""
    try:
        with Image.open(image_path) as img:
            return {
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
                "info": img.info
            }
    except Exception as e:
        print(f"Image metadata error: {e}")
        return {}

# --------------------------------------------------------
# Task Execution Function
# --------------------------------------------------------
async def execute_task_with_pdf(task_id: str, file_path: str, filename: str, task: str, top_k_sources: int):
    """Execute a task with PDF in background"""
    try:
        task_queue[task_id] = {
            "status": "processing",
            "message": f"Extracting text from {filename}...",
            "progress": 20
        }
        
        # Extract text
        document_text = extract_text_from_pdf(file_path)
        
        if not document_text:
            task_queue[task_id] = {
                "status": "error",
                "message": "Could not extract text from PDF",
                "progress": 100
            }
            return
        
        task_queue[task_id] = {
            "status": "processing",
            "message": f"Executing task: {task[:50]}...",
            "progress": 40
        }
        
        # Execute the task
        result = await run_task_with_document(task, document_text, top_k_sources)
        
        # Store result
        task_results[task_id] = {
            "status": "completed",
            "result": result,
            "metadata": {
                "filename": filename,
                "task": task,
                "extracted_text_length": len(document_text),
                "completed_at": datetime.now().isoformat()
            }
        }
        
        task_queue[task_id] = {
            "status": "completed",
            "message": f"Task completed successfully",
            "progress": 100
        }
        
        # Save to DB
        try:
            save_task_result(
                task_id=task_id,
                filename=filename,
                task=task,
                result=json.dumps(result),
                status="completed"
            )
        except Exception as e:
            print(f"DB save error: {e}")
            
    except Exception as e:
        print(f"Task execution error: {e}")
        task_queue[task_id] = {
            "status": "error",
            "message": f"Error: {str(e)}",
            "progress": 100
        }
    finally:
        # Clean up
        try:
            os.unlink(file_path)
        except:
            pass

async def execute_image_analysis(task_id: str, file_path: str, filename: str, task: str):
    """Execute image analysis in background"""
    try:
        task_queue[task_id] = {
            "status": "processing",
            "message": f"Processing image {filename}...",
            "progress": 30
        }
        
        # Analyze image with OCR
        result = await analyze_image_with_llm_and_ocr(file_path, task, max_tokens=600)
        
        # Get image metadata
        metadata = get_image_metadata(file_path)
        
        # Add metadata to result
        result.update({
            "filename": filename,
            "image_metadata": metadata,
            "task_completed_at": datetime.now().isoformat()
        })
        
        # Store result
        task_results[task_id] = {
            "status": "completed",
            "result": result,
            "metadata": {
                "filename": filename,
                "task": task,
                "image_metadata": metadata,
                "completed_at": datetime.now().isoformat()
            }
        }
        
        task_queue[task_id] = {
            "status": "completed",
            "message": f"Image analysis completed",
            "progress": 100
        }
        
        # Save to DB
        try:
            save_task_result(
                task_id=task_id,
                filename=filename,
                task=task,
                result=json.dumps(result),
                status="completed"
            )
        except Exception as e:
            print(f"DB save error: {e}")
            
    except Exception as e:
        print(f"Image analysis error: {e}")
        task_queue[task_id] = {
            "status": "error",
            "message": f"Error: {str(e)}",
            "progress": 100
        }
    finally:
        # Clean up
        try:
            os.unlink(file_path)
        except:
            pass

# --------------------------------------------------------
# Home
# --------------------------------------------------------
@app.get("/")
def home():
    return {
        "message": "AI Agent Task Execution System 🚀",
        "status": "ready",
        "endpoints": {
            "text_research": "POST /run_research",
            "chat": "POST /chat",
            "pdf_task": "POST /execute_pdf_task",
            "image_analysis": "POST /analyze_image",
            "quick_pdf_analysis": "POST /quick_pdf_analysis",
            "task_status": "GET /task_status/{task_id}",
            "task_result": "GET /task_result/{task_id}",
            "history": "GET /history"
        }
    }

# --------------------------------------------------------
# Run Research (TEXT / QUERY)
# --------------------------------------------------------
@app.post("/run_research")
async def run_research(req: ResearchRequest):
    result = await run_research_pipeline(req.query, req.top_k_sources)

    # Save to DB
    try:
        research = result.get("research", {})
        sources_str = json.dumps(research.get("sources", [])) if isinstance(research.get("sources"), list) else research.get("sources", "")
        notes = research.get("notes", "")
        summary = result.get("summary", "")
        critique = result.get("critique", {}).get("critique", "")
        final_report = result.get("final", "")
        
        save_history(req.query, sources_str, notes, summary, critique, final_report)
    except Exception as e:
        print(f"DB save skipped: {e}")

    return result

# --------------------------------------------------------
# Chat Endpoint (LLM only)
# --------------------------------------------------------
@app.post("/chat")
def chat(req: ChatRequest):
    prompt = f"""
You are a helpful AI assistant. Reply conversationally to the user's message.

User: {req.message}

Assistant:"""
    
    try:
        resp = groq_generate(prompt, max_tokens=req.max_tokens)
        return {"response": resp}
    except Exception as e:
        return {"error": str(e)}

# --------------------------------------------------------
# Analyze Image Endpoint - UPDATED WITH OCR
# --------------------------------------------------------
@app.post("/analyze_image")
async def analyze_image(
    file: UploadFile = File(...),
    task: str = "Describe this image"
):
    """Analyze uploaded image with OCR capability"""
    
    # Validate file type
    valid_image_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/bmp']
    if file.content_type not in valid_image_types:
        raise HTTPException(status_code=400, detail=f"Only image files are supported. Got: {file.content_type}")
    
    # Create temporary file
    suffix = '.png' if 'png' in file.content_type else '.jpg'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Analyze image with OCR and LLM
        result = await analyze_image_with_llm_and_ocr(tmp_path, task, max_tokens=700)
        
        # Add file info
        result.update({
            "filename": file.filename,
            "file_size": len(content),
            "content_type": file.content_type,
            "upload_timestamp": datetime.now().isoformat()
        })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass

# --------------------------------------------------------
# Quick PDF Analysis (Direct, no background task)
# --------------------------------------------------------
@app.post("/quick_pdf_analysis")
async def quick_pdf_analysis(
    file: UploadFile = File(...),
    task: str = "Analyze this document",
    top_k_sources: int = 3
):
    """Direct PDF analysis without background task"""
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Extract text
        document_text = extract_text_from_pdf(tmp_path)
        
        if not document_text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF. The PDF might be scanned or image-based.")
        
        # Execute task
        result = await run_task_with_document(task, document_text, top_k_sources)
        
        # Add metadata
        result["task_metadata"] = {
            "filename": file.filename,
            "task": task,
            "extracted_text_length": len(document_text),
            "execution_time": datetime.now().isoformat(),
            "user_query_addressed": task
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task execution failed: {str(e)}")
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass

# --------------------------------------------------------
# Execute Task with PDF (Background task version)
# --------------------------------------------------------
@app.post("/execute_pdf_task")
async def execute_pdf_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    task: str = "Analyze this document",
    top_k_sources: int = 3
):
    """
    Execute AI agent task on uploaded PDF.
    """
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    # Initialize task status
    task_queue[task_id] = {
        "status": "queued",
        "message": f"Task queued: {task[:50]}...",
        "progress": 10
    }
    
    # Start background task
    background_tasks.add_task(
        execute_task_with_pdf,
        task_id, tmp_path, file.filename, task, top_k_sources
    )
    
    return {
        "task_id": task_id,
        "status": "queued",
        "message": f"Task started: {task[:50]}...",
        "filename": file.filename,
        "progress": 10,
        "check_status_url": f"/task_status/{task_id}",
        "get_result_url": f"/task_result/{task_id}"
    }

# --------------------------------------------------------
# Execute Image Analysis (Background task version)
# --------------------------------------------------------
@app.post("/execute_image_analysis")
async def execute_image_analysis_background(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    task: str = "Describe this image"
):
    """
    Execute image analysis in background.
    """
    
    # Validate file type
    valid_image_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp']
    if file.content_type not in valid_image_types:
        raise HTTPException(status_code=400, detail=f"Only image files are supported. Got: {file.content_type}")
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Create temporary file
    suffix = '.png' if file.content_type == 'image/png' else '.jpg'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    # Initialize task status
    task_queue[task_id] = {
        "status": "queued",
        "message": f"Image analysis queued: {task[:50]}...",
        "progress": 10
    }
    
    # Start background task
    background_tasks.add_task(
        execute_image_analysis,
        task_id, tmp_path, file.filename, task
    )
    
    return {
        "task_id": task_id,
        "status": "queued",
        "message": f"Image analysis started: {task[:50]}...",
        "filename": file.filename,
        "progress": 10,
        "check_status_url": f"/task_status/{task_id}",
        "get_result_url": f"/task_result/{task_id}"
    }

# --------------------------------------------------------
# Task Status
# --------------------------------------------------------
@app.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a task"""
    if task_id not in task_queue:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_queue[task_id]

# --------------------------------------------------------
# Task Result
# --------------------------------------------------------
@app.get("/task_result/{task_id}")
async def get_task_result(task_id: str):
    """Get result of completed task"""
    if task_id not in task_results:
        if task_id in task_queue and task_queue[task_id]["status"] == "completed":
            # Task completed but result not stored yet
            return {
                "status": "completed",
                "message": "Task completed but result is being processed",
                "progress": 100
            }
        raise HTTPException(status_code=404, detail="Task result not found")
    
    return task_results[task_id]

# --------------------------------------------------------
# List Active Tasks
# --------------------------------------------------------
@app.get("/active_tasks")
async def list_active_tasks():
    """List all active tasks"""
    active_tasks = []
    for task_id, status in task_queue.items():
        if status["status"] in ["queued", "processing"]:
            active_tasks.append({
                "task_id": task_id,
                **status
            })
    
    return {
        "active_tasks": active_tasks,
        "total": len(active_tasks)
    }

# --------------------------------------------------------
# History Endpoint
# --------------------------------------------------------
@app.get("/history")
def history():
    rows = get_history()
    output = []
    
    for r in rows:
        output.append({
            "id": r[0],
            "query": r[1],
            "sources": r[2],
            "notes": r[3],
            "summary": r[4],
            "critique": r[5],
            "final_report": r[6],
            "created_at": r[7]
        })
    
    return output

# --------------------------------------------------------
# Test Endpoint for Image Analysis
# --------------------------------------------------------
@app.post("/test_image_analysis")
async def test_image_analysis(req: ImageAnalysisRequest):
    """Test image analysis without file"""
    try:
        # Create a test image path (this would be replaced with actual image in real use)
        test_result = {
            "task": req.task,
            "analysis": f"Test analysis for: '{req.task}'. Upload an actual image for real OCR text extraction.",
            "extracted_text": "This is test extracted text. Real images will show actual text content.",
            "ocr_success": True,
            "test_mode": True
        }
        
        return test_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

# --------------------------------------------------------
# Direct OCR Endpoint (just extract text)
# --------------------------------------------------------
@app.post("/extract_text_from_image")
async def extract_text_from_image_endpoint(file: UploadFile = File(...)):
    """Direct OCR text extraction from image"""
    
    # Validate file type
    valid_image_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/bmp']
    if file.content_type not in valid_image_types:
        raise HTTPException(status_code=400, detail=f"Only image files are supported. Got: {file.content_type}")
    
    # Create temporary file
    suffix = '.png' if 'png' in file.content_type else '.jpg'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Extract text using OCR
        text = extract_text_from_image(tmp_path)
        
        # Get image metadata
        metadata = get_image_metadata(tmp_path)
        
        return {
            "filename": file.filename,
            "extracted_text": text,
            "text_length": len(text),
            "word_count": len(text.split()),
            "image_metadata": metadata,
            "success": bool(text.strip()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass