from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import sqlite3
import re
import os

from pydantic import BaseModel

app = FastAPI(title="MCP Server (Model Context Protocol) with SQLite")

# Path to your SQLite DB (update if needed)
DB_PATH = "companies.db"

def get_db_connection():
    """Get a connection to the SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class QueryRequest(BaseModel):
    question: str

def parse_nl_query(question: str) -> str:
    """Convert natural language to SQL query"""
    question = question.lower().strip()
    
    # Simple pattern matching for common queries
    if " all" in question and "companies" in question:
        return 'SELECT "CompanyName", "CompanyNumber", "CompanyStatus" FROM companies LIMIT 10'
    elif "count" in question and "companies" in question:
        return "SELECT COUNT(*) as total_companies FROM companies"
    elif "active" in question and "companies" in question:
        return 'SELECT "CompanyName", "CompanyNumber" FROM companies WHERE "CompanyStatus" = "Active" LIMIT 10'
    elif "dissolved" in question and "companies" in question:
        return 'SELECT "CompanyName", "CompanyNumber", "DissolutionDate" FROM companies WHERE "CompanyStatus" = "Dissolved" LIMIT 10'
    elif "micro" in question and ("entity" in question):
        return 'SELECT "CompanyName", "CompanyNumber", "Accounts.AccountCategory" FROM companies WHERE "Accounts.AccountCategory" = "MICRO ENTITY" LIMIT 10'
    elif "small" in question and ("companies" in question or "business" in question):
        return 'SELECT "CompanyName", "CompanyNumber", "Accounts.AccountCategory" FROM companies WHERE "Accounts.AccountCategory" = "SMALL" LIMIT 10'
    elif "medium" in question and ("companies" in question or "business" in question):
        return 'SELECT "CompanyName", "CompanyNumber", "Accounts.AccountCategory" FROM companies WHERE "Accounts.AccountCategory" = "MEDIUM" LIMIT 10'
    elif "large" in question and ("companies" in question or "business" in question):
        return 'SELECT "CompanyName", "CompanyNumber", "Accounts.AccountCategory" FROM companies WHERE "Accounts.AccountCategory" = "LARGE" LIMIT 10'
    elif "category" in question or "type" in question:
        # Search across both category fields
        # Extract category term from question
        category_terms = []
        if "private" in question and "limited" in question:
            category_terms.append('"CompanyCategory" LIKE "%Private Limited Company%"')
        elif "charitable" in question:
            category_terms.append('"CompanyCategory" LIKE "%Charitable%"')
        elif "community" in question and "interest" in question:
            category_terms.append('"CompanyCategory" LIKE "%Community Interest%"')
        elif "limited" in question and "partnership" in question:
            category_terms.append('"CompanyCategory" LIKE "%Limited Partnership%"')
        elif "overseas" in question:
            category_terms.append('"CompanyCategory" LIKE "%Overseas%"')
        elif "dormant" in question:
            category_terms.append('"Accounts.AccountCategory" = "DORMANT"')
        elif "exemption" in question:
            category_terms.append('"Accounts.AccountCategory" LIKE "%EXEMPTION%"')
        elif "full" in question and "accounts" in question:
            category_terms.append('"Accounts.AccountCategory" = "FULL"')
        elif "no accounts" in question or "no accounts filed" in question:
            category_terms.append('"Accounts.AccountCategory" = "NO ACCOUNTS FILED"')
        elif "unaudited" in question:
            category_terms.append('"Accounts.AccountCategory" LIKE "%UNAUDITED%"')
        elif "group" in question:
            category_terms.append('"Accounts.AccountCategory" = "GROUP"')
        else:
            # Generic category search - search in both fields
            return 'SELECT "CompanyName", " CompanyNumber", "CompanyCategory", "Accounts.AccountCategory" FROM companies WHERE "CompanyCategory" IS NOT NULL OR "Accounts.AccountCategory" IS NOT NULL LIMIT 10'
        
        if category_terms:
            where_clause = " OR ".join(category_terms)
            return f'SELECT "CompanyName", "CompanyNumber", "CompanyCategory", "Accounts.AccountCategory" FROM companies WHERE {where_clause} LIMIT 10'
        else:
            return 'SELECT "CompanyName", "CompanyNumber", "CompanyCategory", "Accounts.AccountCategory" FROM companies LIMIT 10'
    elif "company" in question and "name" in question:
        # Extract company name from question
        match = re.search(r'company\s+(?:named\s+)?([a-zA-Z0-9\s]+)', question)
        if match:
            company_name = match.group(1).strip()
            return f'SELECT * FROM companies WHERE "CompanyName" LIKE "%{company_name}%" LIMIT 5'
        else:
            return 'SELECT "CompanyName", "CompanyNumber" FROM companies LIMIT 10'
    else:
        # Default query
        return 'SELECT "CompanyName", "CompanyNumber", "CompanyStatus" FROM companies LIMIT 10'

@app.post("/query")
@app.get("/query")
async def query_db(request: Optional[QueryRequest] = None, question: Optional[str] = None):
    """Query the database using natural language"""
    query_text = request.question if request else question
    print(f"[DEBUG] Incoming question: {query_text}")
    if not query_text:
        raise HTTPException(status_code=400, detail="Question is required")
    
    try:
        # Parse natural language to SQL
        sql_query = parse_nl_query(query_text)
        print(f"[DEBUG] Generated SQL: {sql_query}")
        
        # Execute query
        conn = get_db_connection()
        cursor = conn.execute(sql_query)
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        
        # Get results
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "sql": sql_query,
            "columns": columns,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        print(f"[ERROR] Query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query error: {e}")

@app.get("/tables", response_model=List[str])
def list_tables():
    """
    List all tables in the SQLite database as MCP resources.
    Returns a list of table names, excluding SQLite's internal tables.
    """
    conn = get_db_connection()
    # Query sqlite_master to get all user-defined tables
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

@app.get("/tables/{table_name}")
def get_resource_schema(table_name: str):
    """
    Get the schema (columns and types) for a given resource (table).
    Returns a list of columns with their names and types.
    """
    conn = get_db_connection()
    try:
        # Use PRAGMA table_info to get column info for the table
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = [dict(name=row[1], type=row[2]) for row in cursor.fetchall()]
        if not columns:
            # Table not found
            raise HTTPException(status_code=404, detail="Resource not found")
        return {"table_name": table_name, "columns": columns}
    finally:
        conn.close()

@app.get("/tables/{table_name}/data")
def read_resource_data(
    table_name: str,
    limit: int = Query(10, ge=1, le=100),  # Maximum number of rows to return
    offset: int = Query(0, ge=0),          # Offset for pagination

    columns: Optional[str] = None,
    filter: Optional[str] = None,
):
    """Read data from a resource (table) with optional filtering, column selection, and pagination."""
    conn = get_db_connection()
    try:
        col_clause = "*"
        if columns:
            col_clause = ", ".join([col.strip() for col in columns.split(",")])
        sql = f"SELECT {col_clause} FROM {table_name}"
        params = []
        if filter:
            sql += f" WHERE {filter}"
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = conn.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        return {"data": rows, "limit": limit, "offset": offset}
    except sqlite3.Error as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

from fastapi import Form
from fastapi.responses import HTMLResponse

@app.get("/ask")
def ask_page():
    """Simple web interface for asking questions"""
    return FileResponse("templates/ask.html")

@app.post("/ask")
async def ask_submit(question: str = Form(...), details: str = Form(None)):
    """Process submitted question from ask.html form and show DB results."""
    error = None
    results = []
    columns = []
    sql_query = ""
    try:
        sql_query = parse_nl_query(question)
        print(sql_query)
        conn = get_db_connection()
        cursor = conn.execute(sql_query)
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        error = str(e)

    # Build results table HTML if there are results
    results_html = ""
    if error:
        results_html = f'<div style="color: red; margin: 16px 0;">Error: {error}</div>'
    elif results:
        results_html = '<table style="width:100%; border-collapse:collapse; margin-top:24px;">'
        results_html += '<tr>' + ''.join(f'<th style="border:1px solid #ccc; padding:6px;">{col}</th>' for col in columns) + '</tr>'
        for row in results:
            results_html += '<tr>' + ''.join(f'<td style="border:1px solid #ccc; padding:6px;">{row[col]}</td>' for col in columns) + '</tr>'
        results_html += '</table>'
    else:
        results_html = '<div style="margin: 16px 0;">No results found.</div>'

    html_content = f"""
    <html>
        <head><title>Ask a Question</title></head>
        <body style='font-family: Arial, sans-serif; background: #f9f9f9;'>
            <div style='max-width: 500px; margin: 60px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 32px 24px;'>
                <h1>Ask a Question</h1>
                <form action="/ask" method="post" style="margin-bottom:24px;">
                    <label for="question">Your Question</label>
                    <textarea id="question" name="question" rows="4" required placeholder="Type your question here...">{question}</textarea>
                    <label for="details">Additional Details (optional)</label>
                    <input type="text" id="details" name="details" value="{details or ''}" placeholder="Add more context if needed">
                    <button type="submit">Submit</button>
                </form>
                <div><strong>SQL Query:</strong> <code>{sql_query}</code></div>
                {results_html}
                <a href="/ask" style="display:block; margin-top:20px;">Ask another question</a>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/")
def root():
    return {"message": "MCP Server for SQLite is running."}
