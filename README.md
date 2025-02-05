# AEC Knowledge Graph Query System

A web-based application for querying and validating Architecture, Engineering, and Construction (AEC) knowledge graphs using natural language. The system uses RDF/SHACL for data representation and validation, and integrates with Google's Gemini AI for natural language processing.

## Features

- **Natural Language Querying**: Convert natural language questions into SPARQL queries
- **SHACL Validation**: Automatic validation of RDF data against predefined SHACL shapes
- **File Management**: Upload and analyze various file types including PDFs, images, and documents
- **Interactive UI**: Modern web interface with real-time query results and file summaries
- **Validation Badge**: Visual indicator showing the validation status of the knowledge graph

## Core Components

- `chatbot_app.py`: Main FastAPI application with web interface and API endpoints
- `knowledge_graph.ttl`: RDF data representing building information
- `shapes.ttl`: SHACL shapes defining data validation rules
- `dsp_functies.py`: Core functionality for API integration and SPARQL query generation

## Data Model

The knowledge graph includes information about:
- Buildings (address, construction year, architect)
- Rooms (type, area, steel beams)
- Permits (issuer, dates, scope)
- Steel Beams (diameter, material grade)

## Requirements

```
fastapi==0.109.0
uvicorn==0.27.0
google-generativeai==0.3.2
rdflib==7.0.0
PyPDF2==3.0.1
python-docx==1.1.0
pandas==2.2.0
openpyxl==3.1.2
Pillow==10.2.0
python-multipart==0.0.9
pydantic==2.6.1
pyshacl==0.25.0
marked==0.0.3
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create an API key file:
   ```bash
   echo "your-gemini-api-key" > api_key.txt
   ```

3. Run the application:
   ```bash
   python chatbot_app.py
   ```

## Usage

1. Access the web interface at `http://localhost:8000`
2. Upload relevant AEC files through the upload interface
3. Use natural language to query the knowledge graph
4. View SHACL validation status in the environment page

## Example Queries

- "What is the diameter of Steel Beam 3 in Room X of Building Y?"
- "Who issued the building permit for Building A?"
- "What are the allowed modifications under the current permit?"

## SHACL Validation

The system validates the following aspects:
- Building properties (address, construction year, rooms)
- Permit details (issuer, dates, scope)
- Room specifications (type, area, steel beams)
- Steel beam properties (diameter, material grade)

## License

MIT License

Copyright (c) 2024 Rens Roelen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. 
