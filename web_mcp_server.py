#!/usr/bin/env python3
"""
Web MCP Server for Companies Database
HTTP endpoints for querying company data with natural language
"""

import json
import sqlite3
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Try to import OpenAI
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("OpenAI not installed. Install with: pip install openai")

# Database file
DB_PATH = "companies.db"

app = FastAPI(title="Companies Database MCP Server", version="1.0.0")

class QueryRequest(BaseModel):
    question: str

class WebMCPServer:
    def __init__(self):
        self.db_path = DB_PATH
        
        # Initialize OpenAI if available
        if HAS_OPENAI:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                openai.api_key = api_key
                self.llm_available = True
                print("OpenAI LLM ready!")
            else:
                self.llm_available = False
                print("No OpenAI API key found. Set OPENAI_API_KEY environment variable.")
        else:
            self.llm_available = False
            print("OpenAI not available. Using fallback pattern matching.")
        
        # Get database schema
        self.schema = self.get_database_schema()
    
    def get_database_schema(self):
        """Get database schema for LLM context"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("PRAGMA table_info(companies)")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "name": row[1],
                    "type": row[2]
                })
            conn.close()
            
            # Get sample data
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("SELECT * FROM companies LIMIT 3")
            sample_data = []
            for row in cursor.fetchall():
                sample_data.append(dict(zip([col[1] for col in cursor.description], row)))
            conn.close()
            
            return {
                "table": "companies",
                "columns": columns,
                "sample_data": sample_data
            }
        except Exception as e:
            print(f"Error getting schema: {e}")
            return {"table": "companies", "columns": [], "sample_data": []}
    
    async def query_companies(self, question: str) -> Dict[str, Any]:
        """Convert question to SQL and execute"""
        # Use LLM or fallback
        if self.llm_available:
            sql_query = await self.llm_to_sql(question)
        else:
            sql_query = self.fallback_to_sql(question)
        
        try:
            # Execute query
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(sql_query)
            
            # Get results
            columns = [description[0] for description in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                "question": question,
                "sql_query": sql_query,
                "results": results,
                "count": len(results),
                "columns": columns,
                "llm_used": self.llm_available
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Query error: {e}")
    
    async def llm_to_sql(self, question: str) -> str:
        """Use OpenAI to convert natural language to SQL"""
        try:
            schema_info = json.dumps(self.schema, indent=2)
            
            prompt = f"""
You are a SQL expert. Convert the user's question into a SQL query for a SQLite database.

Database Schema:
{schema_info}

Important notes:
- Use double quotes around column names that contain spaces or special characters
- The table name is "companies"
- Limit results to 10 rows unless specifically asked for more
- Be careful with column names that have spaces (like " CompanyNumber")

User question: {question}

Return ONLY the SQL query, nothing else:
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a SQL expert. Return only SQL queries, no explanations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            # Clean up response
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            
            return sql_query.strip()
            
        except Exception as e:
            print(f"LLM error: {e}")
            return self.fallback_to_sql(question)
    
    def fallback_to_sql(self, question: str) -> str:
        """Fallback pattern matching"""
        question_lower = question.lower()
        
        if "list" in question_lower and "companies" in question_lower:
            return 'SELECT "CompanyName", " CompanyNumber", "CompanyStatus" FROM companies LIMIT 10'
        elif "count" in question_lower and "companies" in question_lower:
            return "SELECT COUNT(*) as total_companies FROM companies"
        elif "active" in question_lower and "companies" in question_lower:
            return 'SELECT "CompanyName", " CompanyNumber" FROM companies WHERE "CompanyStatus" = "Active" LIMIT 10'
        elif "micro" in question_lower and "entity" in question_lower:
            return 'SELECT "CompanyName", " CompanyNumber", "Accounts.AccountCategory" FROM companies WHERE "Accounts.AccountCategory" = "MICRO ENTITY" LIMIT 10'
        elif "small" in question_lower and "companies" in question_lower:
            return 'SELECT "CompanyName", " CompanyNumber", "Accounts.AccountCategory" FROM companies WHERE "Accounts.AccountCategory" = "SMALL" LIMIT 10'
        elif "private" in question_lower and "limited" in question_lower:
            return 'SELECT "CompanyName", " CompanyNumber", "CompanyCategory" FROM companies WHERE "CompanyCategory" LIKE "%Private Limited Company%" LIMIT 10'
        elif "charitable" in question_lower:
            return 'SELECT "CompanyName", " CompanyNumber", "CompanyCategory" FROM companies WHERE "CompanyCategory" LIKE "%Charitable%" LIMIT 10'
        elif "dormant" in question_lower:
            return 'SELECT "CompanyName", " CompanyNumber", "Accounts.AccountCategory" FROM companies WHERE "Accounts.AccountCategory" = "DORMANT" LIMIT 10'
        else:
            return 'SELECT "CompanyName", " CompanyNumber", "CompanyStatus" FROM companies LIMIT 5'

# Initialize server
server = WebMCPServer()

@app.get("/")
def root():
    """Root endpoint with basic info"""
    return {
        "message": "Companies Database MCP Server",
        "version": "1.0.0",
        "endpoints": {
            "POST /query": "Ask questions about companies",
            "GET /query": "Ask questions via URL parameter",
            "GET /ask": "Web interface for asking questions",
            "GET /schema": "Get database schema",
            "GET /health": "Check server health"
        },
        "llm_available": server.llm_available
    }

@app.post("/query")
async def query_companies_post(request: QueryRequest):
    """POST endpoint for querying companies"""
    return await server.query_companies(request.question)

@app.get("/query")
async def query_companies_get(question: str):
    """GET endpoint for querying companies"""
    if not question:
        raise HTTPException(status_code=400, detail="Question parameter is required")
    return await server.query_companies(question)

@app.get("/schema")
def get_schema():
    """Get database schema"""
    return {
        "schema": server.schema,
        "llm_available": server.llm_available
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT COUNT(*) FROM companies")
        count = cursor.fetchone()[0]
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "total_companies": count,
            "llm_available": server.llm_available
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")

@app.get("/ask", response_class=HTMLResponse)
def ask_page():
    """Web interface for asking questions"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ask About Companies</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 50px auto; 
                padding: 20px; 
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #333; text-align: center; }
            input { 
                width: 70%; 
                padding: 12px; 
                margin: 10px 0; 
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 16px;
            }
            button { 
                padding: 12px 24px; 
                background: #007cba; 
                color: white; 
                border: none; 
                cursor: pointer; 
                border-radius: 4px;
                font-size: 16px;
                margin-left: 10px;
            }
            button:hover { background: #005a87; }
            #result { 
                margin-top: 20px; 
                padding: 15px; 
                background: #f8f9fa; 
                white-space: pre-wrap; 
                border-radius: 4px;
                border-left: 4px solid #007cba;
                font-family: 'Courier New', monospace;
                font-size: 14px;
            }
            .loading { color: #666; font-style: italic; }
            .error { color: #d32f2f; background: #ffebee; border-left-color: #d32f2f; }
            .status { 
                text-align: center; 
                padding: 10px; 
                margin-bottom: 20px; 
                border-radius: 4px;
                font-weight: bold;
            }
            .llm-available { background: #e8f5e8; color: #2e7d32; }
            .llm-unavailable { background: #fff3e0; color: #f57c00; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Ask About Companies Database</h1>
            
            <div id="status" class="status">
                <span id="status-text">Loading...</span>
            </div>
            
            <form id='form'>
                <input type='text' id='question' placeholder='Ask a question about companies...' required>
                <button type='submit'>Ask</button>
            </form>
            
            <div id='result'></div>
        </div>
        
        <script>
            // Check server status
            fetch('/health')
                .then(res => res.json())
                .then(data => {
                    const statusDiv = document.getElementById('status');
                    const statusText = document.getElementById('status-text');
                    
                    if (data.llm_available) {
                        statusDiv.className = 'status llm-available';
                        statusText.textContent = `✅ LLM Available - ${data.total_companies} companies in database`;
                    } else {
                        statusDiv.className = 'status llm-unavailable';
                        statusText.textContent = `⚠️ LLM Not Available - Using pattern matching (${data.total_companies} companies)`;
                    }
                })
                .catch(err => {
                    document.getElementById('status-text').textContent = '❌ Server Error';
                });
            
            // Handle form submission
            document.getElementById('form').onsubmit = async function(e) {
                e.preventDefault();
                const question = document.getElementById('question').value;
                const resultDiv = document.getElementById('result');
                
                resultDiv.innerHTML = '<span class="loading">Loading...</span>';
                resultDiv.className = '';
                
                try {
                    const res = await fetch('/query', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ question: question })
                    });
                    
                    const data = await res.json();
                    
                    if (data.results && data.results.length > 0) {
                        resultDiv.innerHTML = 
                            `Question: ${data.question}\n` +
                            `SQL: ${data.sql_query}\n` +
                            `LLM Used: ${data.llm_used ? 'Yes' : 'No'}\n\n` +
                            `Results (${data.count} rows):\n${JSON.stringify(data.results, null, 2)}`;
                    } else {
                        resultDiv.innerHTML = 
                            `Question: ${data.question}\n` +
                            `SQL: ${data.sql_query}\n` +
                            `LLM Used: ${data.llm_used ? 'Yes' : 'No'}\n\n` +
                            `No results found.`;
                    }
                } catch (err) {
                    resultDiv.innerHTML = 'Error: ' + err.message;
                    resultDiv.className = 'error';
                }
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 