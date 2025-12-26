from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import tempfile
import fitz  # PyMuPDF
import json
import uuid
from datetime import datetime
import base64
import io
from PIL import Image
import requests
import pymupdf as fitz
import pytesseract
import shutil
import os

# Railpack usually puts tesseract here
tesseract_path = shutil.which("tesseract") or "/usr/bin/tesseract"

if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    print(f"✅ Tesseract found at: {tesseract_path}")
else:
    print("❌ CRITICAL: Tesseract NOT found")
# Import your custom modules
from orchestrator import run_research_pipeline, run_task_with_document
from db import init_db, save_history, get_history, save_task_result
from llm_groq import groq_generate
from ocr_utils import extract_text_from_image, analyze_image_content

# --------------------------------------------------------
# 1. YOUR CUSTOM UI (PASTE YOUR HTML/CSS/JS INSIDE THE TRIPLE QUOTES)
# --------------------------------------------------------
HTML_UI = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>AI Multi-Agent Research — Neon UI + Floating Terminal (Upgraded)</title>

<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

<style>
:root{
  --bg:#01010a; --card:#0a0f24; --accent:#00eaff; --accent2:#7b41ff; --accent3:#00ffc6;
  --text:#dff9ff; --muted:#7c8a9a; --radius:16px; --glass: rgba(255,255,255,0.03);
  font-family: "Inter", sans-serif;
}

/* Page */
html,body{margin:0;padding:0;background:var(--bg);color:var(--text);min-height:100vh}
body::before{
  content:"";position:fixed;inset:0;
  background:linear-gradient(90deg, rgba(0,255,255,0.02) 1px, transparent 1px),
             linear-gradient(0deg, rgba(0,255,255,0.02) 1px, transparent 1px);
  background-size:40px 40px; animation:gridMove 18s linear infinite; z-index:-1;
}
@keyframes gridMove{from{background-position:0 0}to{background-position:0 200px}}

.container{max-width:1150px;margin:40px auto;padding:20px}

/* Neon card */
.neon-card{background:var(--card);border-radius:16px;padding:22px;border:1px solid rgba(0,255,255,0.1);
  box-shadow:0 0 25px rgba(0,255,255,0.18),0 0 40px rgba(123,65,255,0.12);backdrop-filter:blur(8px);transition:0.3s;
  position:relative; overflow:hidden;}
.neon-card::before{
  content:"";position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,var(--accent),var(--accent3),var(--accent2));
  opacity:0.4; animation:scanline 3s linear infinite;
}
@keyframes scanline{
  0%{transform:translateX(-100%)}
  100%{transform:translateX(100%)}
}
.neon-card:hover{border-color:var(--accent);box-shadow:0 0 35px rgba(0,255,255,0.35),0 0 60px rgba(123,65,255,0.2)}

/* Glitch effect for headers */
@keyframes glitch{
  0%{transform:translate(0)}
  20%{transform:translate(-2px,2px)}
  40%{transform:translate(-2px,-2px)}
  60%{transform:translate(2px,2px)}
  80%{transform:translate(2px,-2px)}
  100%{transform:translate(0)}
}

header{display:flex;align-items:center;gap:18px;margin-bottom:28px}
header h1{margin:0;font-size:32px;font-weight:800;font-family:"Orbitron", sans-serif;
  background:linear-gradient(90deg,#00eaff,#7b41ff,#00ffc6,#00eaff);
  background-size:300% 100%; -webkit-background-clip:text;color:transparent;
  animation:gradientFlow 3s ease infinite; position:relative;
  text-shadow:0 0 20px rgba(0,255,255,0.3);
}
@keyframes gradientFlow{
  0%{background-position:0% 50%}
  50%{background-position:100% 50%}
  100%{background-position:0% 50%}
}

/* Form Elements */
textarea,input{
  width:100%;padding:14px;border-radius:12px;background:rgba(5,7,29,0.8);
  border:1.5px solid rgba(0,255,255,0.15);color:var(--text);font-family:"Inter", sans-serif;
  font-size:15px;transition:all 0.3s ease;
}
textarea:focus,input:focus{
  outline:none;border-color:var(--accent3);box-shadow:0 0 20px rgba(0,255,255,0.2);
  background:rgba(5,7,29,0.9);
}

label{font-size:14px;font-weight:600;color:var(--accent);margin-bottom:8px;display:block}

button{
  padding:12px 20px;border-radius:12px;border:none;cursor:pointer;font-weight:700;
  text-transform:uppercase;letter-spacing:1px;font-family:"Orbitron", sans-serif;
  background:linear-gradient(90deg,var(--accent3),var(--accent),var(--accent2));
  color:#000;box-shadow:0 0 15px rgba(0,255,255,0.4);transition:all 0.3s ease;
  position:relative; overflow:hidden;
}
button::before{
  content:"";position:absolute;top:0;left:-100%;width:100%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,0.2),transparent);
  transition:0.5s;
}
button:hover{transform:translateY(-3px);box-shadow:0 0 25px rgba(0,255,255,0.6)}
button:hover::before{left:100%}
button:active{transform:translateY(-1px)}

.copy-btn{
  background:transparent;border:1.5px solid var(--accent);color:var(--accent);
  padding:10px 16px;font-size:13px;font-weight:600;position:relative;
}
.copy-btn::after{
  content:"";position:absolute;bottom:0;left:0;width:100%;height:2px;
  background:var(--accent);transform:scaleX(0);transition:transform 0.3s ease;
}
.copy-btn:hover{background:rgba(0,255,255,0.1);color:var(--text)}
.copy-btn:hover::after{transform:scaleX(1)}

/* Grid Layout */
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px}
.full{grid-column:1 / -1}
.small{color:var(--muted);font-size:13px;font-weight:500;letter-spacing:0.5px}

/* Pre/Code blocks */
pre{
  background:rgba(5,7,29,0.9);border-radius:14px;padding:18px;white-space:pre-wrap;
  max-height:280px;overflow:auto;border:1px solid rgba(0,255,255,0.08);
  font-family:"Monaco","Consolas","Courier New",monospace;font-size:14px;line-height:1.5;
  position:relative;
}
pre::before{
  content:"";position:absolute;top:0;right:0;width:12px;height:100%;
  background:linear-gradient(90deg,transparent,rgba(0,255,255,0.05));
}
pre:hover{border-color:rgba(0,255,255,0.2)}

/* Scrollbar styling */
pre::-webkit-scrollbar{width=8px}
pre::-webkit-scrollbar-track{background:rgba(0,0,0,0.2);border-radius:4px}
pre::-webkit-scrollbar-thumb{background:var(--accent);border-radius:4px}
pre::-webkit-scrollbar-thumb:hover{background:var(--accent3)}

@media(max-width:920px){.grid{grid-template-columns:1fr}}

/* Spinner/Loader */
.spinner{
  width:20px;height:20px;border:3px solid rgba(0,255,255,0.15);
  border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;
  display:inline-block;
}
@keyframes spin{to{transform:rotate(360deg)}}

/* Floating Terminal */
#terminal{
  position:fixed;right:24px;bottom:24px;width:420px;max-width:calc(100% - 40px);height:420px;
  z-index:9999;border-radius:16px;overflow:hidden;display:flex;flex-direction:column;
  border:1px solid rgba(0,255,255,0.2);background:linear-gradient(180deg,rgba(4,10,26,0.98),rgba(2,4,10,0.98));
  box-shadow:0 10px 50px rgba(0,0,0,0.7),0 0 40px rgba(0,255,255,0.1);
  transition:transform 0.3s ease,opacity 0.3s ease;backdrop-filter:blur(10px);
}

#termHeader{
  padding:12px 16px;background:linear-gradient(90deg,rgba(0,255,255,0.05),rgba(123,65,255,0.05));
  border-bottom:1px solid rgba(255,255,255,0.05);display:flex;align-items:center;gap:10px;
  cursor:grab;
}
#termHeader .title{
  font-weight:800;color:var(--accent);font-size:14px;font-family:"Orbitron", sans-serif;
  letter-spacing:1px;
}
#termHeader .small-muted{font-size:11px;color:var(--muted);margin-left:8px}
#termHeader .controls{margin-left:auto;display:flex;gap:12px;align-items:center}

#termBody{
  padding:16px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:12px;
}
.msg{
  max-width:88%;padding:12px 16px;border-radius:14px;font-family:"Monaco","Consolas",monospace;
  font-size:13px;line-height:1.4;position:relative;overflow:hidden;
}
.msg::before{
  content:"";position:absolute;top:0;left:0;width:3px;height=100%;background:var(--accent);
  opacity:0.5;
}
.msg.user{
  align-self:flex-end;background:linear-gradient(90deg,#183041,#0f1a28);
  color:#dfefff;border:1px solid rgba(255,255,255,0.05);margin-left:auto;
}
.msg.ai{
  align-self:flex-start;background:linear-gradient(90deg,rgba(0,255,255,0.07),rgba(123,65,255,0.05));
  color:#eaffff;border:1px solid rgba(0,255,255,0.1);
}

.typing{
  display:inline-block;height:10px;width=40px;border-radius:12px;
  background:linear-gradient(90deg,#0ff,#7b41ff);box-shadow:0 0 15px rgba(0,255,255,0.3);
  animation:pulse 1.2s infinite;
}
@keyframes pulse{
  0%{opacity:0.3;transform:scale(0.95)}
  50%{opacity:1;transform:scale(1)}
  100%{opacity:0.3;transform:scale(0.95)}
}

#termFooter{
  display:flex;gap:10px;padding:12px 16px;border-top:1px solid rgba(255,255,255,0.05);
  align-items:center;background:linear-gradient(180deg,rgba(255,255,255,0.02),transparent)
}
#termInput{
  flex:1;padding:10px 14px;border-radius:10px;background:rgba(5,7,29,0.8);
  border:1px solid rgba(0,255,255,0.1);color:var(--text);font-family:monospace;
}
.modeBadge{
  padding:6px 10px;border-radius:8px;background:rgba(0,0,0,0.4);color:var(--accent);
  font-weight:700;border:1px solid rgba(0,255,255,0.1);font-size:12px;
  font-family:"Orbitron", sans-serif;letter-spacing:0.5px;
}

/* Collapsed bubble */
#termCollapsed{
  position:fixed;right:30px;bottom:30px;width:60px;height:60px;border-radius:50%;
  background:linear-gradient(90deg,var(--accent),var(--accent2));color:#000;
  display:flex;align-items:center;justify-content:center;box-shadow:0 10px 40px rgba(0,0,0,0.7);
  cursor:pointer;z-index:9998;font-weight:800;font-family:"Orbitron", sans-serif;
  font-size:18px;transition:all 0.3s ease;border:2px solid rgba(255,255,255,0.1);
  animation:float 3s ease-in-out infinite;
}
@keyframes float{
  0%,100%{transform:translateY(0)}
  50%{transform:translateY(-10px)}
}
#termCollapsed.visible{
  display:flex;animation:bounceIn 0.3s ease;
}
@keyframes bounceIn{
  0%{transform:scale(0.3) rotate(-180deg);opacity:0}
  50%{transform:scale(1.1) rotate(0)}
  100%{transform:scale(1) rotate(0);opacity:1}
}

/* Left dock button */
#leftDock{
  position:fixed;left:18px;bottom:160px;width:48px;height:48px;border-radius:12px;
  z-index:9998;background:linear-gradient(90deg,#242e40,#15202a);border:1px solid rgba(255,255,255,0.05);
  display:flex;align-items:center;justify-content:center;color:var(--accent);cursor:pointer;
  box-shadow:0 8px 25px rgba(0,0,0,0.6);transition:transform 0.2s ease;font-size:20px;
}
#leftDock:hover{transform:scale(1.15) rotate(5deg)}

/* Fullscreen mode */
#terminal.fullscreen{
  position:fixed!important;left:0!important;top:0!important;right:0!important;bottom:0!important;
  width:100%!important;height=100%!important;border-radius:0!important;transform:none!important;
}

/* Control buttons */
.control-btn{
  cursor:pointer;color:var(--accent);transition:all 0.3s ease;display:flex;
  align-items:center;justify-content:center;width:26px;height:26px;border-radius:6px;
  font-size:14px;
}
.control-btn:hover{
  color:var(--accent3);background:rgba(0,255,255,0.15);transform:scale(1.15);
}

/* Upload Popup */
.upload-popup-overlay{
  position:fixed;top:0;left:0;width:100%;height=100%;background:rgba(0,0,0,0.9);
  backdrop-filter:blur(10px);z-index:10000;display:none;justify-content:center;
  align-items:center;animation:fadeIn 0.3s ease;
}
@keyframes fadeIn{from{opacity:0} to{opacity:1}}

.upload-popup{
  background:var(--card);border-radius:20px;padding:30px;width:90%;max-width:520px;
  border:1px solid rgba(0,255,255,0.25);box-shadow:0 0 60px rgba(0,255,255,0.3),
    0 0 90px rgba(123,65,255,0.25);position:relative;animation:slideUp 0.4s ease;
}
@keyframes slideUp{
  from{transform:translateY(30px);opacity:0}
  to{transform:translateY(0);opacity:1}
}

.upload-popup-header{
  display:flex;justify-content:space-between;align-items:center;margin-bottom:25px;
}
.upload-popup-header h3{
  margin:0;color:var(--accent);font-size:22px;font-family:"Orbitron", sans-serif;
  background:linear-gradient(90deg,var(--accent),var(--accent3));-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;letter-spacing:1px;
}

.close-popup{
  background:transparent;border:none;color:var(--accent);font-size:28px;cursor:pointer;
  width:36px;height:36px;display:flex;align-items:center;justify-content:center;
  border-radius:50%;transition:all 0.3s ease;
}
.close-popup:hover{
  background:rgba(255,0,0,0.25);color:#ff6b6b;transform:rotate(90deg);
}

.upload-options{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:18px;
  margin-bottom:30px;
}
.upload-option{
  background:rgba(5,7,29,0.8);border:2px solid rgba(0,255,255,0.15);border-radius:14px;
  padding:22px 16px;text-align:center;cursor:pointer;transition:all 0.3s ease;
  display:flex;flex-direction:column;align-items:center;gap:14px;
}
.upload-option:hover{
  border-color:var(--accent);background:rgba(0,255,255,0.08);transform:translateY(-5px);
  box-shadow:0 8px 30px rgba(0,255,255,0.2);
}
.upload-option i{font-size:36px;color:var(--accent)}
.upload-option span{color:var(--text);font-weight:600;font-size:15px}
.upload-option small{color:var(--muted);font-size:12px;margin-top:6px}

.upload-drop-zone{
  border:3px dashed rgba(0,255,255,0.35);border-radius:16px;padding:35px 25px;
  text-align:center;margin-bottom:25px;cursor:pointer;transition:all 0.3s ease;
}
.upload-drop-zone:hover{
  border-color:var(--accent);background:rgba(0,255,255,0.05);
}
.upload-drop-zone i{font-size:52px;color:var(--accent);margin-bottom:18px}
.upload-drop-zone p{color:var(--text);margin:12px 0;font-size:16px}
.upload-drop-zone .small{color:var(--muted);font-size:13px}

.file-input{display:none}

.uploaded-files{
  max-height:220px;overflow-y:auto;margin-top:25px;display:none;
}
.uploaded-files.active{display:block}
.uploaded-file{
  background:rgba(5,7,29,0.9);border-radius:12px;padding:14px 18px;margin-bottom:12px;
  border:1px solid rgba(0,255,255,0.15);display:flex;justify-content:space-between;
  align-items:center;animation:fadeInUp 0.3s ease;
}
@keyframes fadeInUp{
  from{opacity:0;transform:translateY(15px)}
  to{opacity:1;transform:translateY(0)}
}

.file-info{display:flex;align-items:center;gap:14px;flex:1;overflow:hidden}
.file-icon{color:var(--accent);font-size:22px;min-width:22px}
.file-details{flex:1;min-width:0;overflow:hidden}
.file-name{
  color:var(--text);font-size:15px;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;font-weight:500;
}
.file-size{color:var(--muted);font-size:13px;margin-top:4px}
.remove-file{
  background:rgba(255,0,0,0.15);border:1px solid rgba(255,0,0,0.3);color:#ff6b6b;
  border-radius:8px;padding:8px 14px;cursor:pointer;font-size:13px;transition:all 0.3s ease;
}
.remove-file:hover{
  background:rgba(255,0,0,0.25);transform:scale(1.08);
}

/* Query bar with icons */
.query-bar-container{position:relative;width:100%}
#query{
  width:100%;box-sizing:border-box;padding-right:150px!important;
  min-height:130px;resize:vertical;font-size:15px;line-height:1.6;
}
.query-icons{
  position:absolute;right:18px;top:18px;display:flex;gap:12px;align-items:center;
  z-index:10;
}
.query-icon{
  width:40px;height:40px;border-radius:10px;display:flex;align-items:center;
  justify-content:center;cursor:pointer;transition:all 0.3s ease;
  background:rgba(0,255,255,0.15);border:1.5px solid rgba(0,255,255,0.25);
  color:var(--accent);position:relative;flex-shrink:0;
}
.query-icon:hover{
  background:rgba(0,255,255,0.25);border-color:var(--accent);transform:translateY(-3px);
  box-shadow:0 8px 20px rgba(0,255,255,0.3);
}
.query-icon.recording{
  background:rgba(255,0,0,0.25);border-color:rgba(255,0,0,0.4);color:#ff6b6b;
  animation:pulseRed 1.2s infinite;
}
@keyframes pulseRed{
  0%,100%{box-shadow:0 0 15px rgba(255,0,0,0.5)}
  50%{box-shadow:0 0 25px rgba(255,0,0,0.9)}
}

.file-count-badge{
  position:absolute;top:-6px;right:-6px;background:var(--accent3);color:#000;
  font-size:11px;font-weight:bold;width:20px;height:20px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;z-index:11;font-family:"Orbitron", sans-serif;
}

.upload-status{
  margin-top:12px;padding:10px 14px;border-radius:10px;background:rgba(0,255,255,0.08);
  border:1px solid rgba(0,255,255,0.15);font-size:13px;color:var(--accent);
  display:none;width:100%;box-sizing:border-box;font-weight:500;
}
.upload-status.active{
  display:block;animation:fadeIn 0.3s ease;
}
.upload-status.error{
  color:#ff6b6b;border-color:rgba(255,0,0,0.35);background:rgba(255,0,0,0.12);
}
.upload-status.success{
  color:var(--accent3);border-color:rgba(0,255,198,0.35);background:rgba(0,255,198,0.12);
}

/* Voice status indicator */
.voice-status-indicator{
  position:fixed;top:24px;right:24px;background:rgba(0,0,0,0.85);border:1px solid rgba(255,0,0,0.45);
  padding:12px 18px;border-radius:12px;color:white;font-size:14px;display:none;
  align-items:center;gap:10px;z-index:10001;backdrop-filter:blur(12px);
  animation:slideInRight 0.3s ease;font-weight:500;
}
@keyframes slideInRight{
  from{transform:translateX(30px);opacity:0}
  to{transform:translateX(0);opacity:1}
}
.voice-status-indicator.active{display:flex}
.voice-status-indicator i{color:#ff6b6b;animation:pulse 1.5s infinite}

/* Image preview */
.image-preview{
  max-width:100%;max-height:220px;border-radius:12px;margin-top:12px;
  border:1px solid rgba(0,255,255,0.25);display:none;
}
.image-preview.active{
  display:block;animation:fadeIn 0.3s ease;
}

/* Analysis results styling */
.result-card{
  background:rgba(5,7,29,0.7);border-radius:14px;padding:18px;margin:8px 0;
  border-left:4px solid var(--accent);
}
.result-header{
  color:var(--accent);font-weight:600;font-size:15px;margin-bottom:10px;
  display:flex;align-items:center;gap:8px;
}
.result-content{
  color:var(--text);font-size:14px;line-height:1.6;
}
.keyword-item{
  display:inline-block;background:rgba(0,255,255,0.1);border:1px solid rgba(0,255,255,0.2);
  border-radius:8px;padding:6px 12px;margin:4px;font-size:13px;transition:all 0.3s ease;
}
.keyword-item:hover{
  background:rgba(0,255,255,0.2);transform:translateY(-2px);
  box-shadow:0 4px 12px rgba(0,255,255,0.15);
}

/* Critique section styling */
.critique-section{
  background:rgba(5,7,29,0.8);border-radius:14px;padding:16px;margin:10px 0;
  border:1px solid rgba(255,255,255,0.05);
}
.critique-title{
  color:var(--accent3);font-weight:600;font-size:14px;margin-bottom:8px;
  display:flex;align-items:center;gap:8px;
}
.critique-point{
  background:rgba(255,100,100,0.1);border-left:3px solid rgba(255,100,100,0.5);
  padding:10px 12px;margin:8px 0;border-radius:6px;font-size:13px;
}

/* Responsive */
@media(max-width:768px){
  .query-icons{right:12px;top:12px;gap:10px}
  .query-icon{width:36px;height:36px}
  #query{padding-right:130px!important;min-height:110px}
}
@media(max-width:480px){
  .query-icons{right:10px;top:10px;gap:8px}
  .query-icon{width:34px;height:34px}
  #query{padding-right:120px!important}
}

/* Download button special */
#downloadBtn{
  background:linear-gradient(90deg,#ff6b6b,#ff8e53);
  box-shadow:0 0 20px rgba(255,107,107,0.4);
}
#downloadBtn:hover{
  box-shadow:0 0 30px rgba(255,107,107,0.6);
  background:linear-gradient(90deg,#ff8e53,#ff6b6b);
}

/* Tag styling */
.tag{
  display:inline-block;background:rgba(123,65,255,0.15);color:var(--accent2);
  padding:4px 10px;border-radius:20px;font-size:12px;font-weight:600;
  margin:0 4px 8px 0;border:1px solid rgba(123,65,255,0.3);
}

/* Footer */
footer{
  margin-top:25px;padding:20px;background:rgba(5,7,29,0.6);border-radius:14px;
  text-align:center;border:1px solid rgba(0,255,255,0.1);
  font-size:13px;color:var(--muted);
}
footer span{
  color:var(--accent3);font-weight:600;font-family:"Orbitron", sans-serif;
}

/* Fancy text effects */
.glow-text{
  text-shadow:0 0 10px currentColor,0 0 20px currentColor;
}
.pulse-text{
  animation:pulse 2s infinite;
}
</style>
</head>
<body>

<div class="container">
  <header>
    <svg width="46" height="46" viewBox="0 0 24 24" style="filter: drop-shadow(0 0 10px var(--accent))">
      <path fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" 
            d="M12 2L20 7v6c0 5-4 9-8 9s-8-4-8-9V7z M12 17v4"/>
      <circle cx="12" cy="13" r="1" fill="var(--accent3)"/>
    </svg>
    <h1>AI Multi-Agent Research System</h1>
  </header>

  <div class="neon-card">
    <label>Enter Research Query or Task</label>
    <div class="query-bar-container">
      <textarea id="query" placeholder="Type your query or task here → 
Example: Impact of AGI on economy 
OR Upload PDF/Image and enter: What does this image show? 
OR Extract text from this document"></textarea>
      <div class="query-icons">
        <div class="query-icon" id="voiceCommandIcon" title="Voice Command">
          <i class="fas fa-microphone"></i>
        </div>
        <div class="query-icon" id="uploadTriggerIcon" title="Upload Files">
          <i class="fas fa-paperclip"></i>
          <div class="file-count-badge" id="fileCountBadge" style="display: none;">0</div>
        </div>
        <div class="query-icon" id="clearQueryIcon" title="Clear Query">
          <i class="fas fa-times"></i>
        </div>
      </div>
    </div>
    
    <div class="upload-status" id="uploadStatus"></div>
    
    <!-- Image Preview -->
    <img id="imagePreview" class="image-preview" alt="Image Preview">
    
    <div style="margin-top:16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
      <label style="width:auto;min-width:120px">Analysis Mode</label>
      <select id="analysisMode" style="background:rgba(5,7,29,0.9);color:var(--text);border:1.5px solid rgba(0,255,255,0.2);border-radius:10px;padding:10px 14px;width:180px;font-weight:500">
        <option value="auto">Auto Detect</option>
        <option value="text">Text Analysis</option>
        <option value="pdf">PDF Analysis</option>
        <option value="image">Image Analysis</option>
      </select>
      <div style="flex:1;min-width:100px"></div>
      <button id="runBtn" style="background:linear-gradient(90deg,var(--accent3),var(--accent))">Execute Task</button>
      <button id="clearAllBtn" class="copy-btn">Reset All</button>
    </div>
    <div id="status" class="small" style="margin-top:12px;display:flex;align-items:center;gap:8px"></div>
  </div>

  <div class="grid">
    <div class="neon-card">
      <div class="small">Research (Sources + Notes)</div>
      <pre id="research">—</pre>
      <button class="copy-btn" data-copy-target="research">Copy</button>
    </div>

    <div class="neon-card">
      <div class="small">Summary (TL;DR)</div>
      <pre id="summary">—</pre>
      <button class="copy-btn" data-copy-target="summary">Copy</button>
    </div>

    <div class="neon-card full">
      <div class="small">Critique (Self-Review)</div>
      <pre id="critique">—</pre>
      <button class="copy-btn" data-copy-target="critique">Copy</button>
    </div>

    <div class="neon-card full">
      <div class="small">Final Research Report / Task Results</div>
      <pre id="final">—</pre>
      <button id="downloadBtn" class="copy-btn">Download PDF Report</button>
    </div>
  </div>

  <div class="neon-card full" style="margin-top:22px">
    <div class="small">Research History (Last 50)</div>
    <pre id="historyBox">—</pre>
    <button class="copy-btn" id="loadHistoryBtn">Load History</button>
  </div>

  <footer>
    Powered by <span class="glow-text" style="color:var(--accent)">Researcher → Summarizer → Critic → Writer</span> Agents 
    <span style="color:var(--accent3); margin-left:10px">+ Multi-Modal Analysis (PDF + Image + Text)</span>
  </footer>
</div>

<!-- Upload Popup -->
<div class="upload-popup-overlay" id="uploadPopup">
  <div class="upload-popup">
    <div class="upload-popup-header">
      <h3>Upload Files for Analysis</h3>
      <button class="close-popup" id="closePopup">&times;</button>
    </div>
    
    <div class="upload-options">
      <div class="upload-option" id="uploadImageOption">
        <i class="fas fa-image"></i>
        <div>
          <span>Upload Image</span>
          <small>PNG, JPG, JPEG, GIF</small>
        </div>
      </div>
      
      <div class="upload-option" id="uploadPdfOption">
        <i class="fas fa-file-pdf"></i>
        <div>
          <span>Upload PDF</span>
          <small>Documents, Reports</small>
        </div>
      </div>
      
      <div class="upload-option" id="uploadAudioOption">
        <i class="fas fa-file-audio"></i>
        <div>
          <span>Upload Audio</span>
          <small>MP3, WAV, M4A</small>
        </div>
      </div>
      
      <div class="upload-option" id="uploadTextOption">
        <i class="fas fa-file-alt"></i>
        <div>
          <span>Upload Text</span>
          <small>TXT, DOC, DOCX</small>
        </div>
      </div>
    </div>
    
    <div class="upload-drop-zone" id="uploadDropZone">
      <i class="fas fa-cloud-upload-alt"></i>
      <p>Drag & drop files here</p>
      <p class="small">or click to browse (Max 10MB each)</p>
      <input type="file" id="fileInput" class="file-input" multiple accept=".pdf,.png,.jpg,.jpeg,.gif,.mp3,.wav,.m4a,.txt,.doc,.docx">
    </div>
    
    <div class="uploaded-files" id="uploadedFiles">
      <!-- Files will be added here dynamically -->
    </div>
    
    <div style="display:flex;gap:12px;margin-top:25px;">
      <button id="analyzeUploadedBtn" style="flex:1;background:linear-gradient(90deg,var(--accent),var(--accent2))">
        Analyze Uploaded Files
      </button>
      <button id="clearUploadsBtn" class="copy-btn">Clear All</button>
    </div>
  </div>
</div>

<!-- Voice Status Indicator -->
<div class="voice-status-indicator" id="voiceStatusIndicator">
  <i class="fas fa-circle pulse-text"></i>
  <span>Listening for voice command...</span>
</div>

<!-- Floating Terminal -->
<div id="terminal" role="dialog" aria-label="AI terminal">
  <div id="termHeader">
    <div class="title">NEON TERMINAL</div>
    <div class="small-muted">Hybrid Chat • Research • Multi-Modal</div>
    <div class="controls">
      <div class="control-btn" id="fullscreenBtn" title="Full screen">⛶</div>
      <div class="control-btn" id="minimizeBtn" title="Minimize">▁</div>
      <div class="control-btn" id="closeBtn" title="Close">✕</div>
    </div>
  </div>

  <div id="termBody"></div>

  <div id="termFooter">
    <div class="modeBadge" id="modeBadge">Auto</div>
    <input id="termInput" placeholder="Type a message..." />
    <button id="sendBtn" style="padding:10px 16px;font-size:12px">Send</button>
  </div>
</div>

<!-- Collapsed bubble -->
<div id="termCollapsed" title="Open AI Terminal">AI</div>

<!-- Left dock button -->
<div id="leftDock" title="Open AI Terminal">💬</div>

<!-- Include jsPDF library -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>

<script>
// ================== INITIALIZATION ==================
const term = document.getElementById('terminal');
const termCollapsed = document.getElementById('termCollapsed');
const minimizeBtn = document.getElementById('minimizeBtn');
const closeBtn = document.getElementById('closeBtn');
const leftDock = document.getElementById('leftDock');
const fullscreenBtn = document.getElementById('fullscreenBtn');
const queryTextarea = document.getElementById('query');
const imagePreview = document.getElementById('imagePreview');
const analysisMode = document.getElementById('analysisMode');

// State
let isMinimized = false;
let isFullscreen = false;
let uploadedFiles = [];
let isRecordingVoice = false;
let recognition = null;

// ================== QUERY BAR ICONS ==================
const voiceCommandIcon = document.getElementById('voiceCommandIcon');
const uploadTriggerIcon = document.getElementById('uploadTriggerIcon');
const clearQueryIcon = document.getElementById('clearQueryIcon');
const fileCountBadge = document.getElementById('fileCountBadge');
const uploadStatus = document.getElementById('uploadStatus');

// Query bar icons functionality
voiceCommandIcon.addEventListener('click', toggleVoiceCommand);
uploadTriggerIcon.addEventListener('click', openUploadPopup);
clearQueryIcon.addEventListener('click', clearQuery);

function clearQuery() {
  queryTextarea.value = '';
  queryTextarea.focus();
  showUploadStatus('Query cleared', 'info');
}

// ================== UPLOAD POPUP ==================
const uploadPopup = document.getElementById('uploadPopup');
const closePopup = document.getElementById('closePopup');
const fileInput = document.getElementById('fileInput');
const uploadDropZone = document.getElementById('uploadDropZone');
const uploadedFilesContainer = document.getElementById('uploadedFiles');
const analyzeUploadedBtn = document.getElementById('analyzeUploadedBtn');
const clearUploadsBtn = document.getElementById('clearUploadsBtn');
const voiceStatusIndicator = document.getElementById('voiceStatusIndicator');

// Upload option buttons
const uploadImageOption = document.getElementById('uploadImageOption');
const uploadPdfOption = document.getElementById('uploadPdfOption');
const uploadAudioOption = document.getElementById('uploadAudioOption');
const uploadTextOption = document.getElementById('uploadTextOption');

// Open popup
function openUploadPopup() {
  uploadPopup.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  updateUploadedFilesDisplay();
}

// Close popup
closePopup.addEventListener('click', closeUploadPopup);
uploadPopup.addEventListener('click', (e) => {
  if (e.target === uploadPopup) {
    closeUploadPopup();
  }
});

function closeUploadPopup() {
  uploadPopup.style.display = 'none';
  document.body.style.overflow = 'auto';
  updateFileCountBadge();
}

// Upload option clicks
uploadImageOption.addEventListener('click', () => {
  fileInput.accept = '.png,.jpg,.jpeg,.gif,.webp';
  fileInput.click();
});

uploadPdfOption.addEventListener('click', () => {
  fileInput.accept = '.pdf';
  fileInput.click();
});

uploadAudioOption.addEventListener('click', () => {
  fileInput.accept = '.mp3,.wav,.m4a,.ogg';
  fileInput.click();
});

uploadTextOption.addEventListener('click', () => {
  fileInput.accept = '.txt,.doc,.docx,.pdf,.md,.rtf';
  fileInput.click();
});

// Drag and drop
uploadDropZone.addEventListener('click', () => fileInput.click());

uploadDropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadDropZone.style.borderColor = 'var(--accent)';
  uploadDropZone.style.background = 'rgba(0,255,255,0.08)';
});

uploadDropZone.addEventListener('dragleave', () => {
  uploadDropZone.style.borderColor = 'rgba(0,255,255,0.35)';
  uploadDropZone.style.background = '';
});

uploadDropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadDropZone.style.borderColor = 'rgba(0,255,255,0.35)';
  uploadDropZone.style.background = '';
  
  if (e.dataTransfer.files.length) {
    handleFiles(e.dataTransfer.files);
  }
});

// File input change
fileInput.addEventListener('change', (e) => {
  if (e.target.files.length) {
    handleFiles(e.target.files);
  }
});

function handleFiles(files) {
  const validTypes = [
    'application/pdf',
    'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp',
    'audio/mpeg', 'audio/wav', 'audio/mp3', 'audio/mp4', 'audio/ogg',
    'text/plain', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ];
  
  let newFilesCount = 0;
  
  for (let file of files) {
    // Check file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      showUploadStatus(`File ${file.name} is too large (max 10MB)`, 'error');
      continue;
    }
    
    // Check file type
    if (!validTypes.includes(file.type) && !file.name.match(/\.(pdf|png|jpg|jpeg|gif|webp|mp3|wav|m4a|ogg|txt|doc|docx|md|rtf)$/i)) {
      showUploadStatus(`File ${file.name} has unsupported format`, 'error');
      continue;
    }
    
    // Add to uploaded files
    const fileId = Date.now() + Math.random();
    uploadedFiles.push({
      id: fileId,
      file: file,
      name: file.name,
      size: formatFileSize(file.size),
      type: getFileType(file),
      icon: getFileIcon(file.type),
      date: new Date().toLocaleTimeString()
    });
    
    newFilesCount++;
    
    // Show image preview if it's an image
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = function(e) {
        imagePreview.src = e.target.result;
        imagePreview.classList.add('active');
      };
      reader.readAsDataURL(file);
    }
  }
  
  if (newFilesCount > 0) {
    showUploadStatus(`Added ${newFilesCount} file(s)`, 'success');
    updateUploadedFilesDisplay();
    updateFileCountBadge();
    
    // Auto-select analysis mode based on file type
    autoSelectAnalysisMode();
  }
  
  // Clear file input
  fileInput.value = '';
}

function getFileType(file) {
  if (file.type.includes('pdf')) return 'PDF';
  if (file.type.startsWith('image/')) return 'Image';
  if (file.type.startsWith('audio/')) return 'Audio';
  if (file.type.includes('text') || file.name.match(/\.(txt|doc|docx|md|rtf)$/i)) return 'Text';
  return 'File';
}

function getFileIcon(type) {
  if (type.includes('pdf')) return 'fas fa-file-pdf';
  if (type.startsWith('image/')) return 'fas fa-image';
  if (type.startsWith('audio/')) return 'fas fa-file-audio';
  if (type.includes('text') || type.includes('msword') || type.includes('wordprocessingml')) return 'fas fa-file-alt';
  return 'fas fa-file';
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function updateUploadedFilesDisplay() {
  if (uploadedFiles.length === 0) {
    uploadedFilesContainer.classList.remove('active');
    return;
  }
  
  uploadedFilesContainer.classList.add('active');
  uploadedFilesContainer.innerHTML = '';
  
  uploadedFiles.forEach((file, index) => {
    const fileElement = document.createElement('div');
    fileElement.className = 'uploaded-file';
    fileElement.innerHTML = `
      <div class="file-info">
        <i class="${file.icon} file-icon"></i>
        <div class="file-details">
          <div class="file-name" title="${file.name}">${file.name}</div>
          <div class="file-size">${file.size} • ${file.type} • ${file.date}</div>
        </div>
      </div>
      <button class="remove-file" data-index="${index}">
        <i class="fas fa-times"></i>
      </button>
    `;
    uploadedFilesContainer.appendChild(fileElement);
  });
  
  // Add remove event listeners
  uploadedFilesContainer.querySelectorAll('.remove-file').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const index = parseInt(e.currentTarget.dataset.index);
      const removedFile = uploadedFiles.splice(index, 1)[0];
      updateUploadedFilesDisplay();
      updateFileCountBadge();
      showUploadStatus(`Removed: ${removedFile.name}`, 'info');
      
      // Clear image preview if removed file was an image
      if (removedFile.type === 'Image') {
        imagePreview.classList.remove('active');
        imagePreview.src = '';
      }
    });
  });
}

function updateFileCountBadge() {
  if (uploadedFiles.length > 0) {
    fileCountBadge.textContent = uploadedFiles.length;
    fileCountBadge.style.display = 'flex';
    uploadTriggerIcon.style.background = 'rgba(0, 255, 198, 0.3)';
    uploadTriggerIcon.style.borderColor = 'var(--accent3)';
    uploadTriggerIcon.style.color = 'var(--accent3)';
  } else {
    fileCountBadge.style.display = 'none';
    uploadTriggerIcon.style.background = 'rgba(0, 255, 255, 0.15)';
    uploadTriggerIcon.style.borderColor = 'rgba(0, 255, 255, 0.25)';
    uploadTriggerIcon.style.color = 'var(--accent)';
  }
}

function autoSelectAnalysisMode() {
  const hasImage = uploadedFiles.some(f => f.type === 'Image');
  const hasPDF = uploadedFiles.some(f => f.type === 'PDF');
  
  if (hasImage) {
    analysisMode.value = 'image';
    showUploadStatus('Image detected. Analysis mode set to Image Analysis.', 'info');
  } else if (hasPDF) {
    analysisMode.value = 'pdf';
    showUploadStatus('PDF detected. Analysis mode set to PDF Analysis.', 'info');
  } else {
    analysisMode.value = 'text';
  }
}

function showUploadStatus(message, type = 'info') {
  uploadStatus.textContent = message;
  uploadStatus.className = 'upload-status active';
  
  if (type === 'error') {
    uploadStatus.classList.add('error');
  } else if (type === 'success') {
    uploadStatus.classList.add('success');
  } else {
    uploadStatus.classList.remove('error', 'success');
  }
  
  setTimeout(() => {
    uploadStatus.classList.remove('active');
  }, 4000);
}

// Analyze uploaded files
analyzeUploadedBtn.addEventListener('click', async () => {
  if (uploadedFiles.length === 0) {
    showUploadStatus('Please upload files first!', 'error');
    return;
  }
  
  showUploadStatus('Starting analysis...', 'info');
  closeUploadPopup();
  
  // Trigger the main analysis
  setTimeout(() => {
    document.getElementById('runBtn').click();
  }, 500);
});

// Clear all uploads
clearUploadsBtn.addEventListener('click', () => {
  uploadedFiles = [];
  updateUploadedFilesDisplay();
  updateFileCountBadge();
  imagePreview.classList.remove('active');
  imagePreview.src = '';
  showUploadStatus('All files cleared', 'info');
  analysisMode.value = 'auto';
});

// ================== VOICE COMMAND ==================
function toggleVoiceCommand() {
  if (isRecordingVoice) {
    stopVoiceCommand();
  } else {
    startVoiceCommand();
  }
}

function startVoiceCommand() {
  if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
    showUploadStatus('Voice recognition not supported in this browser', 'error');
    return;
  }
  
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = 'en-US';
  
  recognition.onstart = () => {
    isRecordingVoice = true;
    voiceCommandIcon.classList.add('recording');
    voiceStatusIndicator.classList.add('active');
    voiceStatusIndicator.querySelector('span').textContent = 'Listening... Speak now';
    playBeep(800, 0.1);
  };
  
  recognition.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      if (event.results[i].isFinal) {
        transcript += event.results[i][0].transcript;
      } else {
        transcript += event.results[i][0].transcript;
      }
    }
    
    queryTextarea.value = transcript;
    voiceStatusIndicator.querySelector('span').textContent = `Heard: ${transcript.substring(0, 40)}${transcript.length > 40 ? '...' : ''}`;
  };
  
  recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
    stopVoiceCommand();
    showUploadStatus(`Voice error: ${event.error}`, 'error');
  };
  
  recognition.onend = () => {
    if (isRecordingVoice) {
      // Auto-restart if still recording
      setTimeout(() => {
        if (isRecordingVoice) {
          recognition.start();
        }
      }, 100);
    } else {
      stopVoiceCommand();
    }
  };
  
  try {
    recognition.start();
  } catch (error) {
    showUploadStatus('Failed to start voice recognition', 'error');
  }
}

function stopVoiceCommand() {
  isRecordingVoice = false;
  voiceCommandIcon.classList.remove('recording');
  voiceStatusIndicator.classList.remove('active');
  
  if (recognition) {
    recognition.stop();
  }
  
  playBeep(600, 0.1);
}

// ================== MINIMIZE/RESTORE ==================
function minimizeTerminal() {
  term.style.opacity = '0';
  term.style.transform = 'translateY(20px) scale(0.9)';
  
  setTimeout(() => {
    term.style.display = 'none';
    termCollapsed.style.display = 'flex';
    termCollapsed.classList.add('visible');
    isMinimized = true;
  }, 200);
  
  playBeep(600, 0.05);
}

function restoreTerminal() {
  termCollapsed.classList.remove('visible');
  termCollapsed.style.display = 'none';
  
  term.style.display = 'flex';
  term.style.opacity = '0';
  term.style.transform = 'translateY(10px)';
  
  setTimeout(() => {
    term.style.opacity = '1';
    term.style.transform = 'translateY(0)';
    isMinimized = false;
  }, 10);
  
  playBeep(800, 0.05);
}

function toggleTerminal() {
  if (isMinimized) {
    restoreTerminal();
  } else {
    minimizeTerminal();
  }
}

// Event listeners
minimizeBtn.addEventListener('click', toggleTerminal);
closeBtn.addEventListener('click', minimizeTerminal);
termCollapsed.addEventListener('click', restoreTerminal);

leftDock.addEventListener('click', () => {
  restoreTerminal();
  term.style.left = 'auto';
  term.style.right = '24px';
  term.style.top = 'auto';
  term.style.bottom = '24px';
});

// ================== FULLSCREEN ==================
fullscreenBtn.addEventListener('click', () => {
  if (!isFullscreen) {
    term.classList.add('fullscreen');
    isFullscreen = true;
    fullscreenBtn.textContent = '⤢';
  } else {
    term.classList.remove('fullscreen');
    isFullscreen = false;
    fullscreenBtn.textContent = '⛶';
  }
  playBeep(500, 0.04);
});

// ================== SOUND ==================
function playBeep(freq = 880, duration = 0.08) {
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    oscillator.frequency.value = freq;
    oscillator.type = 'sine';
    gainNode.gain.value = 0.03;
    oscillator.start();
    oscillator.stop(audioCtx.currentTime + duration);
  } catch(e) {}
}

// ================== DRAGGABLE ==================
let isDragging = false;
let dragOffsetX = 0;
let dragOffsetY = 0;
const header = document.getElementById('termHeader');

header.addEventListener('mousedown', (e) => {
  if (isFullscreen) return;
  isDragging = true;
  const rect = term.getBoundingClientRect();
  dragOffsetX = e.clientX - rect.left;
  dragOffsetY = e.clientY - rect.top;
  header.style.cursor = 'grabbing';
});

document.addEventListener('mousemove', (e) => {
  if (!isDragging || isFullscreen) return;
  let left = e.clientX - dragOffsetX;
  let top = e.clientY - dragOffsetY;
  
  const pad = 8;
  left = Math.max(pad, Math.min(window.innerWidth - term.offsetWidth - pad, left));
  top = Math.max(pad, Math.min(window.innerHeight - term.offsetHeight - pad, top));
  
  term.style.right = 'auto';
  term.style.left = left + 'px';
  term.style.top = top + 'px';
});

document.addEventListener('mouseup', () => {
  isDragging = false;
  header.style.cursor = 'grab';
});

// ================== CHAT FUNCTIONALITY ==================
// ✅ FIXED FOR RAILWAY: No more localhost!
const API_RESEARCH = "/run_research";
const API_CHAT = "/chat";
const termBody = document.getElementById("termBody");
const termInput = document.getElementById("termInput");
const sendBtn = document.getElementById("sendBtn");
const modeBadge = document.getElementById("modeBadge");

function appendMessage(text, who="ai", typing=false){
  const el = document.createElement("div");
  el.className = "msg " + (who==="user" ? "user" : "ai");
  if(typing){
    el.innerHTML = `<div class="typing"></div>`;
  } else {
    el.textContent = text;
  }
  termBody.appendChild(el);
  termBody.scrollTop = termBody.scrollHeight;
  return el;
}

async function sendMessageFromInput(){
  const text = termInput.value.trim();
  if(!text) return;
  termInput.value = "";
  appendMessage(text, "user");
  playBeep(1200, 0.04);
  modeBadge.textContent = "Chat";

  const typEl = appendMessage("", "ai", true);
  playBeep(650, 0.04);
  
  try {
    const res = await fetch(API_CHAT, {
      method: "POST", 
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ 
        message: text, 
        max_tokens: 500 
      })
    });
    
    if(!res.ok){
      typEl.remove();
      appendMessage("Error: chat server returned " + res.status, "ai");
      return;
    }
    
    const data = await res.json();
    typEl.remove();
    appendMessage(data.response || data.error || "No response", "ai");
    playBeep(1000, 0.04);
    
  } catch(err){
    typEl.remove();
    appendMessage("Error: chat failed.", "ai");
    console.error(err);
  }
}

termInput.addEventListener("keydown", (e)=>{
  if(e.key === "Enter" && !e.shiftKey){
    e.preventDefault(); 
    sendMessageFromInput();
  }
});
sendBtn.addEventListener("click", sendMessageFromInput);

appendMessage("Neon terminal online. Ready for research conversations!", "ai");

// ================== MAIN TASK EXECUTION ==================
document.getElementById("runBtn").addEventListener("click", async ()=>{
  const userTask = queryTextarea.value.trim();
  const mode = analysisMode.value;
  
  // Show status
  document.getElementById("status").innerHTML = '<div class="spinner"></div> Executing task...';
  
  try {
    // Check uploaded files
    const imageFile = uploadedFiles.find(f => f.type === "Image");
    const pdfFile = uploadedFiles.find(f => f.type === "PDF");
    
    // Handle image analysis
    if ((mode === 'image' || (mode === 'auto' && imageFile)) && imageFile) {
      if (!userTask) {
        showUploadStatus("Please enter a task for image analysis!", "error");
        document.getElementById("status").textContent = "No task entered";
        return;
      }
      
      showUploadStatus(`Analyzing image: "${userTask}"`, 'info');
      
      const formData = new FormData();
      formData.append('file', imageFile.file);
      formData.append('task', userTask);
      
      // ✅ FIXED FOR RAILWAY: No more localhost!
      const res = await fetch("/analyze_image", {
        method: "POST",
        body: formData
      });
      
      if (res.ok) {
        const data = await res.json();
        displayImageResults(data, userTask, imageFile.name);
        uploadedFiles = uploadedFiles.filter(f => f.id !== imageFile.id);
        updateFileCountBadge();
      } else {
        const error = await res.text();
        throw new Error(`Image analysis failed: ${error}`);
      }
    }
    // Handle PDF analysis
    else if ((mode === 'pdf' || (mode === 'auto' && pdfFile)) && pdfFile) {
      if (!userTask) {
        showUploadStatus("Please enter a task for the AI agent to execute!", "error");
        document.getElementById("status").textContent = "No task entered";
        return;
      }
      
      showUploadStatus(`Executing task with PDF: "${userTask}"`, 'info');
      
      const formData = new FormData();
      formData.append('file', pdfFile.file);
      
      // ✅ FIXED FOR RAILWAY: No more localhost!
      const res = await fetch(`/quick_pdf_analysis?task=${encodeURIComponent(userTask)}`, {
        method: "POST",
        body: formData
      });
      
      if (res.ok) {
        const data = await res.json();
        
        if (userTask.toLowerCase().includes('keyword') || 
            userTask.toLowerCase().includes('extract') ||
            userTask.toLowerCase().includes('important')) {
          data.task_type = "keyword_extraction";
        }
        
        displayTaskResults(data, userTask);
        uploadedFiles = uploadedFiles.filter(f => f.id !== pdfFile.id);
        updateFileCountBadge();
        
      } else {
        const error = await res.text();
        throw new Error(`PDF task failed: ${error}`);
      }
    }
    else {
      if (!userTask) {
        showUploadStatus("Please enter a query or upload a file!", "error");
        document.getElementById("status").textContent = "No input";
        return;
      }
      
      showUploadStatus('Running research...', 'info');
      
      // ✅ FIXED FOR RAILWAY: No more localhost!
      const res = await fetch("/run_research", {
        method: "POST", 
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ 
          query: userTask, 
          top_k_sources: 3 
        })
      });
      
      if (!res.ok) {
        throw new Error(`Research failed: ${res.status}`);
      }
      
      const data = await res.json();
      
      document.getElementById("research").textContent = formatResearch(data.research);
      document.getElementById("summary").textContent = data.summary || "—";
      document.getElementById("critique").textContent = data.critique?.critique || "—";
      document.getElementById("final").textContent = data.final || "—";
      
      document.getElementById("status").textContent = "Research complete!";
      showUploadStatus('Task completed successfully!', 'success');
    }
    
  } catch(e){
    console.error("Task execution error:", e);
    document.getElementById("status").textContent = "Task failed";
    showUploadStatus(`Error: ${e.message}`, 'error');
  }
});

// Function to display image analysis results
function displayImageResults(data, userTask, filename) {
  let researchContent = `IMAGE: ${filename}\n\nUSER QUERY: ${userTask}\n\n`;
  
  if (data.extracted_text && data.extracted_text.trim()) {
    researchContent += `EXTRACTED TEXT:\n${data.extracted_text}\n\n`;
  }
  
  researchContent += `ANALYSIS:\n${data.analysis || data.response || "No analysis available"}`;
  
  document.getElementById("research").textContent = researchContent;
  
  if (data.extracted_text && data.extracted_text.trim()) {
    document.getElementById("summary").textContent = `OCR extracted ${data.text_length || data.extracted_text.length} characters, ${data.word_count || data.extracted_text.split(' ').length} words`;
  } else if (data.ocr_success === false) {
    document.getElementById("summary").textContent = "No text detected in image";
  } else {
    document.getElementById("summary").textContent = data.summary || "Image analysis completed";
  }
  
  document.getElementById("critique").textContent = data.critique || "Analysis quality check passed";
  document.getElementById("final").textContent = data.detailed_analysis || data.response || data.extracted_text || "Image analysis task completed.";
  
  document.getElementById("status").textContent = `Image analysis complete: ${filename}`;
  showUploadStatus(`Image analysis successful! ${data.ocr_success ? 'Text extracted.' : 'No text found.'}`, 'success');
}

// Function to display task results intelligently
function displayTaskResults(data, userTask) {
  const taskType = data.task_type || data.task_metadata?.task_type || "analysis";
  
  switch(taskType) {
    case "keyword_extraction":
      const keywords = data.keywords || [];
      const analysis = data.analysis || data.response || "";
      
      document.getElementById("research").textContent = `KEYWORDS EXTRACTED:\n\n${keywords.map(k => `• ${k}`).join('\n')}\n\nANALYSIS:\n${analysis}`;
      document.getElementById("summary").textContent = `Extracted ${keywords.length} keywords from the document.`;
      document.getElementById("critique").textContent = "Keyword extraction completed successfully.";
      
      const finalReport = generateKeywordReport(keywords, userTask, analysis);
      document.getElementById("final").textContent = finalReport;
      break;
      
    case "summarization":
      document.getElementById("research").textContent = "DOCUMENT SUMMARY:";
      document.getElementById("summary").textContent = data.response || "—";
      document.getElementById("critique").textContent = `Summary length: ${data.summary_length || 0} characters`;
      
      const summaryReport = generateSummaryReport(data.response, userTask);
      document.getElementById("final").textContent = summaryReport;
      break;
      
    case "date_extraction":
      document.getElementById("research").textContent = "DATES AND TIMELINE:";
      document.getElementById("summary").textContent = data.response || "—";
      document.getElementById("critique").textContent = data.contains_timeline ? "Timeline extracted successfully." : "Date extraction completed.";
      
      const dateReport = generateDateReport(data.response, userTask, data);
      document.getElementById("final").textContent = dateReport;
      break;
      
    default:
      document.getElementById("research").textContent = "TASK ANALYSIS:";
      document.getElementById("summary").textContent = data.response || data.final || "—";
      document.getElementById("critique").textContent = data.critique?.critique || "Analysis completed.";
      document.getElementById("final").textContent = data.response || data.final || `Task "${userTask}" completed successfully.`;
  }
  
  document.getElementById("status").textContent = `Task completed: ${userTask}`;
  showUploadStatus(`Task type: ${taskType}`, 'success');
}

// Helper function to generate keyword extraction report
function generateKeywordReport(keywords, userTask, analysis) {
  const timestamp = new Date().toLocaleString();
  const categories = categorizeKeywords(keywords);
  
  let report = `FINAL RESEARCH REPORT: KEYWORD ANALYSIS\n`;
  report += `═════════════════════════════════════════════\n\n`;
  report += `Task: ${userTask}\n`;
  report += `Generated: ${timestamp}\n`;
  report += `Total Keywords: ${keywords.length}\n\n`;
  
  report += `EXECUTIVE SUMMARY\n`;
  report += `──────────────────\n`;
  report += `This analysis identified ${keywords.length} key terms across ${Object.keys(categories).length} categories.\n\n`;
  
  report += `CATEGORIZED KEYWORDS\n`;
  report += `─────────────────────\n`;
  
  for (const [category, words] of Object.entries(categories)) {
    report += `${category.toUpperCase()} (${words.length}):\n`;
    words.forEach(keyword => {
      report += `   • ${keyword}\n`;
    });
    report += `\n`;
  }
  
  report += `COMPLETE KEYWORD LIST\n`;
  report += `───────────────────────\n`;
  keywords.forEach((keyword, index) => {
    report += `${index + 1}. ${keyword}\n`;
  });
  
  report += `\nANALYSIS INSIGHTS\n`;
  report += `──────────────────\n`;
  report += `${analysis}\n\n`;
  
  report += `RECOMMENDATIONS\n`;
  report += `─────────────────\n`;
  report += `• Explore relationships between keyword categories\n`;
  report += `• Investigate implementation strategies\n`;
  report += `• Examine relevant case studies\n`;
  report += `• Analyze industry trends\n`;
  
  report += `\n═════════════════════════════════════════════\n`;
  report += `Generated by AI Research System`;
  
  return report;
}

// Helper function to categorize keywords
function categorizeKeywords(keywords) {
  const categories = {
    "technology": [],
    "healthcare": [],
    "business": [],
    "challenges": [],
    "solutions": [],
    "other": []
  };
  
  const patterns = {
    technology: ['ai', 'artificial intelligence', 'machine learning', 'tech', 'digital', 'software', 'algorithm', 'data', 'analytics'],
    healthcare: ['health', 'medical', 'patient', 'doctor', 'treatment', 'disease', 'hospital', 'medicine', 'surgery'],
    business: ['business', 'company', 'enterprise', 'startup', 'market', 'industry', 'revenue', 'profit', 'investment'],
    challenges: ['challenge', 'problem', 'issue', 'risk', 'threat', 'difficulty', 'barrier', 'obstacle'],
    solutions: ['solution', 'strategy', 'approach', 'method', 'technique', 'framework', 'model', 'system']
  };
  
  keywords.forEach(keyword => {
    const lowerKeyword = keyword.toLowerCase();
    let categorized = false;
    
    for (const [category, patternList] of Object.entries(patterns)) {
      if (patternList.some(pattern => lowerKeyword.includes(pattern))) {
        categories[category].push(keyword);
        categorized = true;
        break;
      }
    }
    
    if (!categorized) {
      categories.other.push(keyword);
    }
  });
  
  Object.keys(categories).forEach(category => {
    if (categories[category].length === 0) {
      delete categories[category];
    }
  });
  
  return categories;
}

// Helper function for summary reports
function generateSummaryReport(summary, userTask) {
  const timestamp = new Date().toLocaleString();
  
  let report = `FINAL RESEARCH REPORT: DOCUMENT SUMMARY\n`;
  report += `═════════════════════════════════════════════\n\n`;
  report += `Task: ${userTask}\n`;
  report += `Generated: ${timestamp}\n`;
  report += `Length: ${summary.length} characters\n\n`;
  
  report += `EXECUTIVE SUMMARY\n`;
  report += `──────────────────\n`;
  report += `${summary}\n\n`;
  
  report += `KEY TAKEAWAYS\n`;
  report += `────────────────\n`;
  
  const sentences = summary.split(/[.!?]+/).filter(s => s.trim().length > 30);
  sentences.slice(0, 5).forEach((sentence, index) => {
    report += `${index + 1}. ${sentence.trim()}.\n`;
  });
  
  report += `\nIMPLICATIONS\n`;
  report += `──────────────\n`;
  report += `• Review document in full context\n`;
  report += `• Validate against source material\n`;
  report += `• Use as foundation for deeper analysis\n`;
  report += `• Share insights with stakeholders\n`;
  
  report += `\n═════════════════════════════════════════════\n`;
  report += `Generated by AI Research System`;
  
  return report;
}

// Helper function for date extraction reports
function generateDateReport(dateInfo, userTask, data) {
  const timestamp = new Date().toLocaleString();
  
  let report = `FINAL RESEARCH REPORT: TIMELINE ANALYSIS\n`;
  report += `═════════════════════════════════════════════\n\n`;
  report += `Task: ${userTask}\n`;
  report += `Generated: ${timestamp}\n\n`;
  
  report += `TIMELINE RESULTS\n`;
  report += `──────────────────\n`;
  report += `${dateInfo}\n\n`;
  
  if (data.dates && Array.isArray(data.dates)) {
    report += `EXTRACTED DATES\n`;
    report += `─────────────────\n`;
    data.dates.forEach((date, index) => {
      report += `${index + 1}. ${date}\n`;
    });
    report += `\n`;
  }
  
  report += `HISTORICAL CONTEXT\n`;
  report += `────────────────────\n`;
  report += `This document discusses events across multiple time periods.\n`;
  report += `Dates provide context for understanding sequences and developments.\n`;
  
  report += `\nRECOMMENDATIONS\n`;
  report += `────────────────\n`;
  report += `• Verify dates against original document\n`;
  report += `• Cross-reference with historical sources\n`;
  report += `• Analyze temporal patterns\n`;
  report += `• Consider timeline implications\n`;
  
  report += `\n═════════════════════════════════════════════\n`;
  report += `Generated by AI Research System`;
  
  return report;
}

// ================== PDF DOWNLOAD FUNCTIONALITY ==================
document.getElementById("downloadBtn").addEventListener("click", async ()=>{
  const finalReport = document.getElementById("final").textContent;
  if (!finalReport || finalReport.trim() === "—") {
    showUploadStatus("No report content to download!", "error");
    return;
  }
  
  try {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    // Add gradient title
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 234, 255); // Cyan
    doc.setFontSize(24);
    doc.text("AI RESEARCH REPORT", 105, 20, null, null, "center");
    
    // Add subtitle
    doc.setFontSize(12);
    doc.setTextColor(123, 65, 255); // Purple
    doc.text("Generated by AI Multi-Agent System", 105, 30, null, null, "center");
    
    // Add timestamp
    doc.setFontSize(10);
    doc.setTextColor(100, 100, 100);
    doc.text(`Generated: ${new Date().toLocaleString()}`, 105, 38, null, null, "center");
    
    // Add line separator
    doc.setDrawColor(0, 234, 255);
    doc.setLineWidth(0.5);
    doc.line(20, 45, 190, 45);
    
    // Split report into lines
    const lines = doc.splitTextToSize(finalReport, 170);
    
    // Add report content
    doc.setFont("helvetica", "normal");
    doc.setFontSize(11);
    doc.setTextColor(20, 20, 20);
    
    let y = 55;
    for (let i = 0; i < lines.length; i++) {
      if (y > 280) {
        doc.addPage();
        y = 20;
      }
      doc.text(lines[i], 20, y);
      y += 7;
    }
    
    // Add footer
    doc.setFontSize(10);
    doc.setTextColor(150, 150, 150);
    doc.text("Page 1", 105, 290, null, null, "center");
    
    // Save PDF
    doc.save(`AI_Research_Report_${Date.now()}.pdf`);
    showUploadStatus("PDF report downloaded successfully!", "success");
    
  } catch (error) {
    console.error("PDF generation error:", error);
    showUploadStatus("Failed to generate PDF", "error");
    
    // Fallback to text download
    const blob = new Blob([finalReport], {type:"text/plain"});
    const a = document.createElement("a"); 
    a.href = URL.createObjectURL(blob); 
    a.download = `research_report_${Date.now()}.txt`; 
    a.click();
    showUploadStatus("Downloaded as text file", "info");
  }
});

// Clear all button
document.getElementById("clearAllBtn").addEventListener("click", () => {
  queryTextarea.value = "";
  uploadedFiles = [];
  updateUploadedFilesDisplay();
  updateFileCountBadge();
  imagePreview.classList.remove('active');
  imagePreview.src = '';
  document.getElementById("status").textContent = "";
  analysisMode.value = 'auto';
  
  // Clear previews
  document.getElementById("research").textContent = "—";
  document.getElementById("summary").textContent = "—";
  document.getElementById("critique").textContent = "—";
  document.getElementById("final").textContent = "—";
  
  showUploadStatus("All cleared", "info");
});

// History loader - ✅ FIXED FOR RAILWAY: No more localhost!
document.getElementById("loadHistoryBtn").addEventListener("click", async ()=>{
  try {
    document.getElementById("status").innerHTML = '<div class="spinner"></div> Loading history...';
    const res = await fetch("/history");
    const data = await res.json();
    let out = "";
    data.forEach(h => {
      out += `\n#${h.id} — ${h.created_at}\nQuery: ${h.query}\n\nReport:\n${h.final_report}\n\n────────────\n`;
    });
    document.getElementById("historyBox").textContent = out || "No history yet";
    document.getElementById("status").textContent = "History loaded";
  } catch(e){
    document.getElementById("status").textContent = "Failed to load history";
    alert("Failed to load history");
  }
});

// Copy buttons
document.querySelectorAll(".copy-btn[data-copy-target]").forEach(btn=>{
  btn.addEventListener("click", ()=>{
    const tgt = btn.dataset.copyTarget;
    if(!tgt) return;
    const txt = document.getElementById(tgt).textContent;
    navigator.clipboard.writeText(txt);
    const originalText = btn.textContent;
    btn.textContent = "Copied!";
    btn.style.background = "rgba(0,255,198,0.2)";
    btn.style.borderColor = "var(--accent3)";
    setTimeout(()=> {
      btn.textContent = originalText;
      btn.style.background = "";
      btn.style.borderColor = "var(--accent)";
    }, 1500);
  });
});

function formatResearch(r){
  if(!r) return "—";
  let out = "SOURCES:\n";
  (r.sources||[]).forEach((s,i)=> out += `${i+1}. ${s}\n`);
  out += "\nNOTES:\n" + (r.notes || "—");
  return out;
}

</script>
</body>
</html>
"""

app = FastAPI(title="AI Agent Task Execution System")

# Initialize SQLite DB
try:
    init_db()
except Exception as e:
    print(f"DB init note: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------
# 2. SERVE THE UI AT THE ROOT URL
# --------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """This serves your custom UI when you visit the Railway link"""
    return HTML_UI

# --------------------------------------------------------
# Request Models & Task Queues
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

task_queue = {}
task_results = {}

# --------------------------------------------------------
# CORE FUNCTIONS (PDF, IMAGE, TASK EXECUTION)
# --------------------------------------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
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

async def analyze_image_with_llm_and_ocr(image_path: str, task: str = "Describe this image", max_tokens: int = 500) -> Dict[str, Any]:
    try:
        ocr_text = extract_text_from_image(image_path)
        image_analysis = analyze_image_content(image_path)
        
        prompt = f"TASK: {task}\nOCR TEXT: {ocr_text}\nIMAGE INFO: {image_analysis}\n\nAnalyze and respond."
        response = groq_generate(prompt, max_tokens=max_tokens)
        
        return {"analysis": response, "extracted_text": ocr_text, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"error": str(e)}

async def execute_task_with_pdf(task_id: str, file_path: str, filename: str, task: str, top_k_sources: int):
    try:
        task_queue[task_id] = {"status": "processing", "progress": 20}
        document_text = extract_text_from_pdf(file_path)
        if not document_text:
            task_queue[task_id] = {"status": "error", "message": "No text found"}
            return
        
        result = await run_task_with_document(task, document_text, top_k_sources)
        task_results[task_id] = {"status": "completed", "result": result}
        task_queue[task_id] = {"status": "completed", "progress": 100}
        save_task_result(task_id, filename, task, json.dumps(result), "completed")
    except Exception as e:
        task_queue[task_id] = {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(file_path): os.unlink(file_path)

# --------------------------------------------------------
# API ENDPOINTS (ADDING MISSING ONES!)
# --------------------------------------------------------

@app.post("/run_research")
async def run_research(req: ResearchRequest):
    return await run_research_pipeline(req.query, req.top_k_sources)

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Simple chat endpoint for the terminal"""
    try:
        # Simple response using your groq_generate function
        prompt = f"User message: {req.message}\n\nProvide a helpful, concise response."
        response = groq_generate(prompt, max_tokens=req.max_tokens)
        
        # Save to history
        try:
            save_history(req.message, response, "chat")
        except:
            pass
            
        return {"response": response}
    except Exception as e:
        return {"error": str(e)}

@app.post("/analyze_image")
async def analyze_image_endpoint(
    file: UploadFile = File(...),
    task: str = Form("Describe this image")
):
    """Analyze image with OCR and LLM"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Analyze image
        result = await analyze_image_with_llm_and_ocr(tmp_path, task)
        
        # Clean up
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        
        # Add some metadata
        result["filename"] = file.filename
        result["file_size"] = len(content)
        result["task"] = task
        result["timestamp"] = datetime.now().isoformat()
        
        # Save to history
        try:
            save_history(f"Image analysis: {task}", str(result), "image")
        except:
            pass
            
        return result
        
    except Exception as e:
        return {"error": str(e), "message": "Image analysis failed"}
@app.get("/check_ocr")
async def check_ocr():
    import shutil
    path = shutil.which("tesseract")
    return {
        "tesseract_installed": path is not None,
        "path": path,
        "os": os.name
    }    

@app.post("/quick_pdf_analysis")
async def quick_pdf_analysis(
    file: UploadFile = File(...),
    task: str = "Analyze this document"
):
    """Quick PDF analysis endpoint"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Extract text
        text = extract_text_from_pdf(tmp_path)
        if not text:
            return {"error": "No text found in PDF"}
        
        # Simple analysis based on task
        if "keyword" in task.lower() or "extract" in task.lower():
            # Simple keyword extraction
            prompt = f"Extract key keywords and terms from this document:\n\n{text[:2000]}"
        elif "summary" in task.lower():
            prompt = f"Provide a concise summary of this document:\n\n{text[:2000]}"
        else:
            prompt = f"Task: {task}\n\nDocument content:\n{text[:2000]}"
        
        response = groq_generate(prompt, max_tokens=500)
        
        # Clean up
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        
        result = {
            "response": response,
            "filename": file.filename,
            "task": task,
            "text_length": len(text),
            "timestamp": datetime.now().isoformat()
        }
        
        # Save to history
        try:
            save_history(f"PDF analysis: {task}", str(result), "pdf")
        except:
            pass
            
        return result
        
    except Exception as e:
        return {"error": str(e), "message": "PDF analysis failed"}

@app.get("/history")
async def get_history_endpoint():
    """Get research history"""
    try:
        history = get_history(limit=50)
        return history
    except Exception as e:
        return {"error": str(e), "history": []}

@app.post("/execute_pdf_task")
async def execute_pdf_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    task: str = Form(...), # UI uses Form
    top_k_sources: int = Form(3)
):
    task_id = str(uuid.uuid4())
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    task_queue[task_id] = {"status": "queued", "progress": 10}
    background_tasks.add_task(execute_task_with_pdf, task_id, tmp_path, file.filename, task, top_k_sources)
    return {"task_id": task_id, "status": "queued"}

@app.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    return task_queue.get(task_id, {"error": "Not found"})

@app.get("/task_result/{task_id}")
async def get_task_result(task_id: str):
    return task_results.get(task_id, {"error": "Not ready"})

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Helper function for Image Metadata
def get_image_metadata(image_path: str) -> Dict[str, Any]:
    try:
        with Image.open(image_path) as img:
            return {"format": img.format, "size": img.size}
    except: 
        return {}