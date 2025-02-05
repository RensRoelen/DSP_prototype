from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import google.generativeai as genai
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
from typing import List
from pydantic import BaseModel
import PyPDF2
from docx import Document
import pandas as pd
import io
import json
from PIL import Image
import marked
import os
from datetime import datetime
from pyshacl import validate

#  Import functions from function script
from dsp_functies import (
    get_api_key,
    configure_gemini_api,
    generate_sparql_queries,
    query_graph
)

app = FastAPI()

# Initialize the graph and API
api_key = get_api_key()
configure_gemini_api(api_key)
model = genai.GenerativeModel('gemini-pro')
vision_model = genai.GenerativeModel('gemini-pro-vision')

# Store context
context = {}
all_interactions = []

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Store uploaded files info
uploaded_files = []

# Load the knowledge graph from the TTL file
knowledge_graph = Graph()
knowledge_graph.parse("knowledge_graph.ttl", format="ttl")

class QueryRequest(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="en" data-theme="light">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AEC Knowledge Graph Search</title>
        <link href="https://cdn.jsdelivr.net/npm/daisyui@4.6.0/dist/full.min.css" rel="stylesheet" type="text/css" />
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .search-container {
                transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                z-index: 50;
                background-color: white;
            }
            .search-container.centered {
                min-height: 60vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                transform: translateY(0);
            }
            .search-container.top {
                transform: translateY(0);
                box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
                position: sticky;
                top: 0;
            }
            .title-container {
                transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
                opacity: 1;
                transform: translateY(0);
            }
            .title-container.hidden {
                opacity: 0;
                transform: translateY(-20px);
                height: 0;
                margin: 0;
                overflow: hidden;
            }
            .search-form {
                transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
                transform: scale(1);
            }
            .search-container.centered .search-form {
                transform: scale(1.1);
            }
            .result-card {
                transition: opacity 0.3s ease-out;
            }
            .nav-sidebar {
                transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                width: 64px;
                min-height: 100vh;
                position: fixed;
                left: 0;
                top: 0;
                z-index: 100;
                background-color: white;
                box-shadow: 1px 0 3px 0 rgb(0 0 0 / 0.1);
                overflow: hidden;
            }
            .nav-sidebar:hover {
                width: 200px;
            }
            .nav-item {
                display: flex;
                align-items: center;
                padding: 1rem;
                color: #4b5563;
                transition: background-color 0.2s;
                white-space: nowrap;
                overflow: hidden;
            }
            .nav-item:hover {
                background-color: #f3f4f6;
            }
            .nav-item svg {
                width: 24px;
                height: 24px;
                margin-right: 1rem;
                flex-shrink: 0;
            }
            .nav-item span {
                opacity: 0;
                transform: translateX(-10px);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .nav-sidebar:hover .nav-item span {
                opacity: 1;
                transform: translateX(0);
            }
            .main-content {
                margin-left: 64px;
                transition: margin-left 0.3s ease-in-out;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            .upload-zone {
                border: 2px dashed #e5e7eb;
                transition: all 0.3s ease;
            }
            .upload-zone.dragover {
                border-color: #60a5fa;
                background-color: #f0f9ff;
            }
            .title-container {
                min-height: 30vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            .content-area {
                flex: 1;
                padding-bottom: 2rem;
                overflow-y: auto;
            }
            #files-list {
                padding-bottom: 4rem;
            }
        </style>
    </head>
    <body class="min-h-screen bg-base-100">
        <!-- Navigation Sidebar -->
        <nav class="nav-sidebar">
            <a href="/" class="nav-item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span>Home</span>
            </a>
            <a href="/" class="nav-item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <span>Search</span>
            </a>
            <a href="/upload-page" class="nav-item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span>Upload</span>
            </a>
            <a href="/environment" class="nav-item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <span>My Environment</span>
            </a>
        </nav>

        <!-- Main Content -->
        <div class="main-content">
            <!-- Search container (initially centered) -->
            <div id="search-container" class="search-container centered">
                <div class="container mx-auto px-4 py-4">
                    <div id="title-container" class="title-container text-center mb-8">
                        <h1 class="text-4xl font-bold mb-4">AEC Knowledge Graph Search</h1>
                        <p class="text-lg opacity-70">Ask questions about your Build Environment</p>
                    </div>
                    <form id="search-form" class="search-form flex gap-2 max-w-3xl mx-auto">
                        <div class="relative flex-grow">
                            <input type="text" 
                                   placeholder="e.g., What grade of steel is used by the steel beams?" 
                                   class="input input-bordered w-full pr-16" 
                                   id="search-input">
                            <button class="btn btn-primary absolute top-0 right-0 rounded-l-none">Search</button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- Main content area -->
            <div class="container mx-auto px-4 py-8">
                <div id="results" class="space-y-8">
                    <!-- Example queries card (initially visible) -->
                    <div id="example-queries" class="card bg-base-200">
                        <div class="card-body">
                            <p class="text-lg mb-2">Try asking:</p>
                            <ul class="list-disc list-inside space-y-2">
                                <li>"Who is the building permit issued by?"</li>
                                <li>"Which Rooms are there in Building A?"</li>
                                <li>"What does permit X allow?"</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const searchContainer = document.getElementById('search-container');
            const searchForm = document.getElementById('search-form');
            const searchInput = document.getElementById('search-input');
            const results = document.getElementById('results');
            const exampleQueries = document.getElementById('example-queries');
            const titleContainer = document.getElementById('title-container');
            let isFirstQuery = true;

            searchForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const query = searchInput.value.trim();
                if (!query) return;

                if (isFirstQuery) {
                    // Move search to top with animation
                    searchContainer.classList.remove('centered');
                    searchContainer.classList.add('top');
                    titleContainer.classList.add('hidden');
                    
                    // Remove example queries with fade
                    exampleQueries.style.transition = 'opacity 0.3s ease-out';
                    exampleQueries.style.opacity = '0';
                    setTimeout(() => {
                        exampleQueries.remove();
                    }, 300);
                    
                    isFirstQuery = false;
                }

                // Create new result card
                const resultCard = document.createElement('div');
                resultCard.className = 'card bg-base-200 opacity-0 result-card';
                
                // Add query section
                const querySection = document.createElement('div');
                querySection.className = 'card-body border-b border-base-300';
                querySection.innerHTML = `
                    <div class="flex items-center gap-2">
                        <div class="font-semibold">Query:</div>
                        <div>${query}</div>
                    </div>
                `;
                resultCard.appendChild(querySection);

                // Add response section
                const responseSection = document.createElement('div');
                responseSection.className = 'card-body';
                responseSection.innerHTML = `
                    <div class="loading loading-spinner loading-md"></div>
                    <div class="text-sm opacity-70">Searching knowledge graph...</div>
                `;
                resultCard.appendChild(responseSection);

                // Add new result card at the top
                results.insertBefore(resultCard, results.firstChild);
                
                // Trigger fade in
                setTimeout(() => {
                    resultCard.style.opacity = '1';
                }, 10);

                try {
                    const response = await fetch('/query', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ message: query })
                    });
                    
                    const data = await response.json();
                    
                    // Update response section with fade
                    responseSection.style.opacity = '0';
                    setTimeout(() => {
                        responseSection.innerHTML = `
                            <div class="space-y-4">
                                ${data.sparql ? `
                                    <div class="collapse collapse-arrow bg-base-200">
                                        <input type="checkbox" /> 
                                        <div class="collapse-title text-sm font-medium">
                                            View SPARQL Query
                                        </div>
                                        <div class="collapse-content"> 
                                            <pre class="bg-base-300 p-4 rounded-lg overflow-x-auto"><code>${data.sparql}</code></pre>
                                        </div>
                                    </div>
                                ` : ''}
                                <div class="prose">
                                    <div class="font-semibold mb-2">Response:</div>
                                    <div>${data.response}</div>
                                </div>
                            </div>
                        `;
                        responseSection.style.opacity = '1';
                    }, 150);
                } catch (error) {
                    console.error('Error:', error);
                    responseSection.innerHTML = `
                        <div class="text-error">
                            Sorry, something went wrong. Please try again.
                        </div>
                    `;
                }

                // Clear input
                searchInput.value = '';
            });
        </script>
    </body>
    </html>
    """

@app.post("/query")
async def process_query(request: QueryRequest):
    try:
        # Check if any files have been uploaded
        if not uploaded_files:
            return {"response": "Please upload data to your environment before querying the knowledge graph.", "sparql": None}

        # Update context with all previous interactions
        context_description = "\n".join(all_interactions)
        
        # Generate SPARQL queries
        sparql_queries = generate_sparql_queries(request.message, {"context": context_description})
        
        # Try each query until we get a successful result
        for sparql_query in sparql_queries[:5]:  # Try up to 5 queries
            result = query_graph(knowledge_graph, sparql_query)
            if not result.startswith("Error:") and result != "No results found.":
                # Add interaction to history
                all_interactions.append(f"{request.message} -> {result}")
                return {"response": result, "sparql": sparql_query}
        
        return {"response": "No results were found after multiple attempts. Please try rephrasing your query.", "sparql": None}
    except Exception as e:
        return {"response": f"An error occurred: {str(e)}", "sparql": None}

async def analyze_file_content(file: UploadFile) -> str:
    content = await file.read()
    file_extension = file.filename.lower().split('.')[-1]
    
    try:
        if file_extension in ['jpg', 'jpeg', 'png']:
            # Handle images
            image = Image.open(io.BytesIO(content))
            response = vision_model.generate_content([
                "Analyze this image and provide a detailed summary. Focus on any technical or architectural elements if present.",
                image
            ])
            return response.text

        elif file_extension == 'txt':
            # Handle text files
            text = content.decode('utf-8')
            prompt = f"""Analyze the following text content and provide a detailed summary using markdown formatting.
            Use headers (# and ##), bullet points, and other markdown features to structure your response.
            Focus on key information, main topics, and any technical details if present.
            
            Content:
            {text[:5000]}  # First 5000 chars for API limit
            """
            response = model.generate_content(prompt)
            return response.text

        elif file_extension == 'pdf':
            # Handle PDFs
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = ""
            for page in pdf_reader.pages[:3]: 
                text += page.extract_text()

        elif file_extension in ['doc', 'docx']:
            # Handle Word documents
            doc = Document(io.BytesIO(content))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

        elif file_extension in ['csv', 'xlsx', 'xls']:
            # Handle spreadsheets
            if file_extension == 'csv':
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))
            text = f"""# Dataset Overview

## Structure
- **Columns**: {', '.join(df.columns)}
- **Rows**: {len(df)}

## Sample Data
```
{df.head().to_string()}
```
"""

        elif file_extension in ['json', 'xml', 'rdf']:
            # Handle structured data files
            text = f"""# File Content Analysis

```
{content.decode('utf-8')[:1000]}  # First 1000 chars
```
"""
        else:
            return "# Error\nUnsupported file format"

        # Generate summary using Gemini
        prompt = f"""Analyze the following content and provide a detailed summary using markdown formatting. 
        Use headers (# and ##), bullet points, code blocks, and other markdown features to structure your response.
        If it's a technical document or contains architectural/construction information, focus on those aspects.
        If it's data, describe the structure and key insights.
        
        Content:
        {text[:5000]}  # First 5000 chars for API limit
        """
        
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"Error processing file: {str(e)}"

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Save file to disk
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            await file.seek(0)  # Reset file pointer for analysis
        
        # Generate summary
        summary = await analyze_file_content(file)
        
        # Store file info
        file_info = {
            "filename": file.filename,
            "path": file_path,
            "size": os.path.getsize(file_path),
            "upload_date": datetime.now().isoformat(),
            "summary": summary
        }
        uploaded_files.append(file_info)
        
        return {
            "filename": file.filename,
            "status": "success",
            "summary": summary
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/upload-page", response_class=HTMLResponse)
async def upload_page():
    return """
    <!DOCTYPE html>
    <html lang="en" data-theme="light">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AEC File Upload</title>
        <link href="https://cdn.jsdelivr.net/npm/daisyui@4.6.0/dist/full.min.css" rel="stylesheet" type="text/css" />
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            .nav-sidebar {
                transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                width: 64px;
                min-height: 100vh;
                position: fixed;
                left: 0;
                top: 0;
                z-index: 100;
                background-color: white;
                box-shadow: 1px 0 3px 0 rgb(0 0 0 / 0.1);
                overflow: hidden;
            }
            .nav-sidebar:hover {
                width: 200px;
            }
            .nav-item {
                display: flex;
                align-items: center;
                padding: 1rem;
                color: #4b5563;
                transition: background-color 0.2s;
                white-space: nowrap;
                overflow: hidden;
            }
            .nav-item:hover {
                background-color: #f3f4f6;
            }
            .nav-item svg {
                width: 24px;
                height: 24px;
                margin-right: 1rem;
                flex-shrink: 0;
            }
            .nav-item span {
                opacity: 0;
                transform: translateX(-10px);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .nav-sidebar:hover .nav-item span {
                opacity: 1;
                transform: translateX(0);
            }
            .main-content {
                margin-left: 64px;
                transition: margin-left 0.3s ease-in-out;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            .upload-zone {
                border: 2px dashed #e5e7eb;
                transition: all 0.3s ease;
            }
            .upload-zone.dragover {
                border-color: #60a5fa;
                background-color: #f0f9ff;
            }
            .title-container {
                min-height: 30vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            .content-area {
                flex: 1;
                padding-bottom: 2rem;
                overflow-y: auto;
            }
            #files-list {
                padding-bottom: 4rem;
            }
            .markdown-content {
                font-size: 0.95rem;
                line-height: 1.6;
            }
            .markdown-content h1,
            .markdown-content h2,
            .markdown-content h3 {
                font-weight: 600;
                margin-top: 1.5em;
                margin-bottom: 0.5em;
            }
            .markdown-content p {
                margin-bottom: 1em;
            }
            .markdown-content ul,
            .markdown-content ol {
                margin-left: 1.5em;
                margin-bottom: 1em;
            }
            .markdown-content code {
                background-color: #f3f4f6;
                padding: 0.2em 0.4em;
                border-radius: 0.25em;
                font-size: 0.9em;
            }
            .markdown-content pre {
                background-color: #f3f4f6;
                padding: 1em;
                border-radius: 0.5em;
                overflow-x: auto;
                margin-bottom: 1em;
            }
            .markdown-content blockquote {
                border-left: 4px solid #e5e7eb;
                padding-left: 1em;
                margin-left: 0;
                margin-bottom: 1em;
                color: #6b7280;
            }
        </style>
    </head>
    <body class="min-h-screen bg-base-100">
        <!-- Navigation Sidebar -->
        <nav class="nav-sidebar">
            <a href="/" class="nav-item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span>Home</span>
            </a>
            <a href="/" class="nav-item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <span>Search</span>
            </a>
            <a href="/upload-page" class="nav-item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span>Upload</span>
            </a>
            <a href="/environment" class="nav-item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <span>My Environment</span>
            </a>
        </nav>

        <!-- Main Content -->
        <div class="main-content">
            <!-- Title Section -->
            <div class="container mx-auto px-4 py-4">
                <div class="title-container text-center mb-8">
                    <h1 class="text-4xl font-bold mb-4">Upload Files</h1>
                    <p class="text-lg opacity-70">Upload your AEC files to analyze them with our knowledge graph</p>
                </div>
            </div>

            <!-- Upload Section -->
            <div class="content-area">
                <div class="container mx-auto px-4">
                    <div class="max-w-3xl mx-auto">
                        <div id="upload-zone" class="upload-zone rounded-lg p-12 text-center cursor-pointer">
                            <input type="file" 
                                   id="file-input" 
                                   class="hidden" 
                                   multiple
                                   accept=".pdf,.csv,.xlsx,.xls,.doc,.docx,.png,.jpg,.jpeg,.ifc,.rdf,.xml,.json,.txt">
                            <div class="space-y-4">
                                <svg class="mx-auto h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                                </svg>
                                <div class="text-lg">
                                    <span class="text-primary font-semibold">Click to upload</span> or drag and drop
                                </div>
                                <div class="text-sm opacity-70 space-y-1">
                                    <p>Supported formats:</p>
                                    <p>Documents: PDF, Word (.doc, .docx), Text (.txt)</p>
                                    <p>Data: CSV, Excel (.xlsx, .xls)</p>
                                    <p>Images: PNG, JPEG</p>
                                    <p>AEC: IFC, RDF, XML, JSON</p>
                                </div>
                            </div>
                        </div>

                        <!-- Upload Progress and Files List -->
                        <div id="files-list" class="mt-8 space-y-4">
                            <!-- Files will be added here dynamically -->
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const uploadZone = document.getElementById('upload-zone');
            const fileInput = document.getElementById('file-input');
            const filesList = document.getElementById('files-list');

            // Handle drag and drop events
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                uploadZone.addEventListener(eventName, preventDefaults, false);
                document.body.addEventListener(eventName, preventDefaults, false);
            });

            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            ['dragenter', 'dragover'].forEach(eventName => {
                uploadZone.addEventListener(eventName, highlight, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                uploadZone.addEventListener('drop', handleDrop);
            });

            function highlight(e) {
                uploadZone.classList.add('dragover');
            }

            function unhighlight(e) {
                uploadZone.classList.remove('dragover');
            }

            // Handle file selection
            uploadZone.addEventListener('click', () => {
                fileInput.click();
            });

            fileInput.addEventListener('change', handleFiles);
            uploadZone.addEventListener('drop', handleDrop);

            function handleDrop(e) {
                const dt = e.dataTransfer;
                const files = dt.files;
                handleFiles({ target: { files } });
            }

            async function handleFiles(e) {
                const files = [...e.target.files];
                
                for (const file of files) {
                    // Create file item in list
                    const fileItem = document.createElement('div');
                    fileItem.className = 'card bg-base-200';
                    fileItem.innerHTML = `
                        <div class="card-body">
                            <div class="flex items-center justify-between mb-4">
                                <div>
                                    <h3 class="font-semibold">${file.name}</h3>
                                    <p class="text-sm opacity-70">${(file.size / 1024).toFixed(1)} KB</p>
                                </div>
                                <div class="loading loading-spinner loading-md"></div>
                            </div>
                            <div class="space-y-2">
                                <div class="text-sm font-medium">Processing file...</div>
                                <progress class="progress progress-primary w-full"></progress>
                            </div>
                        </div>
                    `;
                    filesList.insertBefore(fileItem, filesList.firstChild);

                    // Upload and process file
                    const formData = new FormData();
                    formData.append('file', file);

                    try {
                        const response = await fetch('/upload', {
                            method: 'POST',
                            body: formData
                        });
                        const data = await response.json();
                        
                        if (data.status === 'success') {
                            fileItem.innerHTML = `
                                <div class="card-body">
                                    <div class="flex items-center justify-between mb-4">
                                        <div>
                                            <h3 class="font-semibold">${file.name}</h3>
                                            <p class="text-sm text-success">Analysis complete</p>
                                        </div>
                                        <svg class="h-6 w-6 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                        </svg>
                                    </div>
                                    <div class="collapse collapse-arrow bg-base-200">
                                        <input type="checkbox" checked /> 
                                        <div class="collapse-title text-sm font-medium">
                                            File Summary
                                        </div>
                                        <div class="collapse-content"> 
                                            <article class="prose prose-sm max-w-none">
                                                <div class="markdown-content">${marked.parse(data.summary)}</div>
                                            </article>
                                        </div>
                                    </div>
                                </div>
                            `;
                        } else {
                            throw new Error('Upload failed');
                        }
                    } catch (error) {
                        fileItem.innerHTML = `
                            <div class="card-body">
                                <div class="flex items-center justify-between">
                                    <div>
                                        <h3 class="font-semibold">${file.name}</h3>
                                        <p class="text-sm text-error">Analysis failed</p>
                                    </div>
                                    <svg class="h-6 w-6 text-error" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </div>
                                <p class="text-sm text-error mt-2">${error.message}</p>
                            </div>
                        `;
                    }
                }
            }
        </script>
    </body>
    </html>
    """

@app.get("/validate-shacl")
async def validate_shacl():
    try:
        # Load and validate the graphs
        shapes_graph = Graph()
        shapes_graph.parse("shapes.ttl", format="turtle")
        
        conforms, _, results_text = validate(
            data_graph=knowledge_graph,
            shacl_graph=shapes_graph,
            inference='rdfs',
            abort_on_first=False,
            meta_shacl=False,
            debug=False
        )
        
        return {
            "conforms": conforms,
            "message": "SHACL Validated" if conforms else "SHACL Validation Failed",
            "details": results_text if not conforms else None
        }
    except Exception as e:
        return {
            "conforms": False,
            "message": "Validation Error",
            "details": str(e)
        }

@app.get("/environment", response_class=HTMLResponse)
async def environment_page():
    return """
    <!DOCTYPE html>
    <html lang="en" data-theme="light">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>My Environment</title>
        <link href="https://cdn.jsdelivr.net/npm/daisyui@4.6.0/dist/full.min.css" rel="stylesheet" type="text/css" />
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            .nav-sidebar {
                transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                width: 64px;
                min-height: 100vh;
                position: fixed;
                left: 0;
                top: 0;
                z-index: 100;
                background-color: white;
                box-shadow: 1px 0 3px 0 rgb(0 0 0 / 0.1);
                overflow: hidden;
            }
            .nav-sidebar:hover {
                width: 200px;
            }
            .nav-item {
                display: flex;
                align-items: center;
                padding: 1rem;
                color: #4b5563;
                transition: background-color 0.2s;
                white-space: nowrap;
                overflow: hidden;
            }
            .nav-item:hover {
                background-color: #f3f4f6;
            }
            .nav-item svg {
                width: 24px;
                height: 24px;
                margin-right: 1rem;
                flex-shrink: 0;
            }
            .nav-item span {
                opacity: 0;
                transform: translateX(-10px);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .nav-sidebar:hover .nav-item span {
                opacity: 1;
                transform: translateX(0);
            }
            .main-content {
                margin-left: 64px;
                transition: margin-left 0.3s ease-in-out;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            .upload-zone {
                border: 2px dashed #e5e7eb;
                transition: all 0.3s ease;
            }
            .upload-zone.dragover {
                border-color: #60a5fa;
                background-color: #f0f9ff;
            }
            .title-container {
                min-height: 30vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            .content-area {
                flex: 1;
                padding-bottom: 2rem;
                overflow-y: auto;
            }
            #files-list {
                padding-bottom: 4rem;
            }
            .shacl-badge {
                display: none;
                align-items: center;
                padding: 0.5rem 1rem;
                border-radius: 9999px;
                font-weight: 500;
                font-size: 0.875rem;
                margin: 1rem auto;
                transition: all 0.3s ease;
                width: fit-content;
            }
            .shacl-badge.valid {
                background-color: #10B981;
                color: white;
            }
            .shacl-badge.invalid {
                background-color: #EF4444;
                color: white;
            }
            .shacl-badge.loading {
                background-color: #6B7280;
                color: white;
            }
            .shacl-badge svg {
                width: 1.25rem;
                height: 1.25rem;
                margin-right: 0.5rem;
            }
            .summary-container {
                max-height: 0;
                overflow: hidden;
                transition: max-height 0.3s ease-out;
            }
            .summary-container.expanded {
                max-height: 2000px;
            }
            .markdown-content {
                font-size: 0.95rem;
                line-height: 1.6;
            }
            .markdown-content h1 { font-size: 1.5rem; font-weight: bold; margin: 1rem 0; }
            .markdown-content h2 { font-size: 1.25rem; font-weight: bold; margin: 0.8rem 0; }
            .markdown-content p { margin: 0.8rem 0; }
            .markdown-content ul { margin-left: 1.5rem; list-style-type: disc; }
            .markdown-content code { background: #f0f0f0; padding: 0.2rem 0.4rem; border-radius: 0.2rem; }
            .markdown-content pre { background: #f0f0f0; padding: 1rem; border-radius: 0.4rem; overflow-x: auto; margin: 1rem 0; }
        </style>
    </head>
    <body class="min-h-screen bg-base-100">
        <!-- Navigation Sidebar -->
        <nav class="nav-sidebar">
            <a href="/" class="nav-item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span>Home</span>
            </a>
            <a href="/" class="nav-item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <span>Search</span>
            </a>
            <a href="/upload-page" class="nav-item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span>Upload</span>
            </a>
            <a href="/environment" class="nav-item">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <span>My Environment</span>
            </a>
        </nav>

        <!-- Main Content -->
        <div class="main-content">
            <!-- Title Section -->
            <div class="container mx-auto px-4 py-4">
                <div class="title-container text-center mb-8">
                    <h1 class="text-4xl font-bold mb-4">My Environment</h1>
                    <p class="text-lg opacity-70 mb-4">View and manage your uploaded files</p>
                    <!-- SHACL Badge (hidden by default) -->
                    <div id="shacl-badge" class="shacl-badge loading">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Checking SHACL validation...
                    </div>
                </div>
            </div>

            <!-- Files Grid -->
            <div class="content-area">
                <div class="container mx-auto px-4">
                    <div class="max-w-6xl mx-auto">
                        <div id="files-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            <!-- Files will be populated here -->
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function loadFiles() {
                const response = await fetch('/list-files');
                const files = await response.json();
                const grid = document.getElementById('files-grid');
                
                if (files.length === 0) {
                    grid.innerHTML = `
                        <div class="col-span-full text-center py-12">
                            <p class="text-lg opacity-70 mb-4">No files uploaded yet</p>
                            <a href="/upload-page" class="btn btn-primary">Upload Files</a>
                        </div>
                    `;
                    document.getElementById('shacl-badge').style.display = 'none';
                    return;
                }

                document.getElementById('shacl-badge').style.display = 'inline-flex';
                checkShaclValidation();

                grid.innerHTML = files.map((file, index) => `
                    <div class="card bg-base-200 shadow-lg">
                        <div class="card-body">
                            <h3 class="card-title text-lg">${file.filename}</h3>
                            <div class="text-sm opacity-70">
                                <p>Size: ${(file.size / 1024).toFixed(1)} KB</p>
                                <p>Uploaded: ${new Date(file.upload_date).toLocaleString()}</p>
                            </div>
                            
                            <div class="mt-4">
                                <button 
                                    onclick="toggleSummary(${index})" 
                                    class="btn btn-sm btn-outline w-full"
                                    id="summary-btn-${index}"
                                >
                                    View Summary
                                </button>
                                
                                <div class="summary-container mt-4" id="summary-${index}">
                                    <div class="markdown-content bg-base-100 rounded-lg p-4">
                                        ${marked.parse(file.summary)}
                                    </div>
                                </div>

                                <a href="/download/${file.filename}" class="btn btn-sm btn-primary w-full mt-4">
                                    Download
                                </a>
                            </div>
                        </div>
                    </div>
                `).join('');
            }

            function toggleSummary(index) {
                const container = document.getElementById(`summary-${index}`);
                const button = document.getElementById(`summary-btn-${index}`);
                container.classList.toggle('expanded');
                button.textContent = container.classList.contains('expanded') ? 'Hide Summary' : 'View Summary';
            }

            async function checkShaclValidation() {
                try {
                    const response = await fetch('/validate-shacl');
                    const data = await response.json();
                    
                    const badge = document.getElementById('shacl-badge');
                    if (data.conforms) {
                        badge.className = 'shacl-badge valid';
                        badge.innerHTML = `
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                            </svg>
                            SHACL Validated
                        `;
                    } else {
                        badge.className = 'shacl-badge invalid';
                        badge.innerHTML = `
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            SHACL Validation Failed
                        `;
                        console.error('Validation details:', data.details);
                    }
                } catch (error) {
                    const badge = document.getElementById('shacl-badge');
                    badge.className = 'shacl-badge invalid';
                    badge.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Validation Error
                    `;
                    console.error('Error checking SHACL validation:', error);
                }
            }

            loadFiles();
        </script>
    </body>
    </html>
    """

@app.get("/list-files")
async def list_files():
    return uploaded_files

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    return {"error": "File not found"}

# Function to validate RDF graph against SHACL shapes
async def validate_rdf_graph(graph: Graph, shapes_file: str) -> bool:
    try:
        conforms, results_graph, results_text = validate(
            data_graph=graph,
            shacl_graph=shapes_file,
            inference='rdfs',
            abort_on_first=False,
            meta_shacl=False,
            debug=False
        )
        return conforms
    except Exception as e:
        print(f"SHACL validation error: {str(e)}")
        return False

@app.get("/search-page", response_class=HTMLResponse)
async def search_page():
    # Validate the RDF graph
    shacl_approved = await validate_rdf_graph(knowledge_graph, "shapes.ttl")
    validation_message = "SHACL APPROVED" if shacl_approved else "SHACL validation failed. Please check the RDF graph."

    return f"""
    <!DOCTYPE html>
    <html lang="en" data-theme="light">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AEC Knowledge Graph Search</title>
        <link href="https://cdn.jsdelivr.net/npm/daisyui@4.6.0/dist/full.min.css" rel="stylesheet" type="text/css" />
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .validation-message {{
                color: green;
                font-weight: bold;
                margin-bottom: 1rem;
            }}
        </style>
    </head>
    <body class="min-h-screen bg-base-100">
        <!-- Validation Message -->
        <div class="validation-message">{validation_message}</div>
        <!-- Rest of the search page content -->
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 