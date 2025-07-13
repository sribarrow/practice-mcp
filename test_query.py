#!/usr/bin/env python3

import sqlite3
import re

# Path to your SQLite DB
DB_PATH = "companies.db"

def get_db_connection():
    """Get a connection to the SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def parse_natural_language_query(question: str) -> str:
    """Convert natural language to SQL query"""
    question = question.lower().strip()
    
    # Simple pattern matching for common queries
    if "list" in question and "companies" in question:
        return 'SELECT "CompanyName", " CompanyNumber", "CompanyStatus" FROM companies LIMIT 10'
    elif "count" in question and "companies" in question:
        return "SELECT COUNT(*) as total_companies FROM companies"
    elif "active" in question and "companies" in question:
        return 'SELECT "CompanyName", " CompanyNumber" FROM companies WHERE "CompanyStatus" = "Active" LIMIT 10'
    elif "dissolved" in question and "companies" in question:
        return 'SELECT "CompanyName", " CompanyNumber", "DissolutionDate" FROM companies WHERE "CompanyStatus" = "Dissolved" LIMIT 10'
    elif "company" in question and "name" in question:
        # Extract company name from question
        match = re.search(r'company\s+(?:named\s+)?([a-zA-Z0-9\s]+)', question)
        if match:
            company_name = match.group(1).strip()
            return f'SELECT * FROM companies WHERE "CompanyName" LIKE "%{company_name}%" LIMIT 5'
        else:
            return 'SELECT "CompanyName", " CompanyNumber" FROM companies LIMIT 10'
    else:
        # Default query
        return 'SELECT "CompanyName", " CompanyNumber", "CompanyStatus" FROM companies LIMIT 10'

def test_query(question: str):
    """Test the query function"""
    print(f"Testing question: {question}")
    
    try:
        # Parse natural language to SQL
        sql_query = parse_natural_language_query(question)
        print(f"Generated SQL: {sql_query}")
        
        # Execute query
        conn = get_db_connection()
        cursor = conn.execute(sql_query)
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        print(f"Columns: {columns}")
        
        # Get results
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        print(f"Results count: {len(results)}")
        
        if results:
            print(f"First result: {results[0]}")
        
        conn.close()
        
        return {
            "sql": sql_query,
            "columns": columns,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Test the query
    result = test_query("list companies")
    if result:
        print("Query successful!")
    else:
        print("Query failed!") 