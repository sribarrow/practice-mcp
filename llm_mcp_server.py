#!/usr/bin/env python3
"""
LLM-Powered MCP Server for Companies Database
Uses an actual LLM to convert natural language to SQL queries
"""

import asyncio
import json
import sqlite3
import os
from typing import Dict, Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

# Try to import OpenAI (you'll need to install it: pip install openai)
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("OpenAI not installed. Install with: pip install openai")

# Database file
DB_PATH = "companies.db"

class LLMMCPServer:
    def __init__(self):
        self.server = Server("llm-companies-server")
        self.db_path = DB_PATH
        
        # Initialize OpenAI client if available
        if HAS_OPENAI:
            api_key = os.getenv("OPENAI_KEY")
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
        
        # Get database schema for LLM context
        self.schema = self.get_database_schema()
        
        # Register our tools
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)
    
    def get_database_schema(self):
        """Get the database schema to help the LLM understand the data"""
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
            
            # Get some sample data for context
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
    
    async def list_tools(self):
        """Tell the client what tools we have"""
        return [
            {
                "name": "ask_about_companies",
                "description": "Ask questions about the companies database using natural language. The LLM will convert your question to SQL and return the results.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Your question about the companies (e.g., 'show me companies in London', 'find companies with more than 100 employees', 'which companies were incorporated in 2020?')"
                        }
                    },
                    "required": ["question"]
                }
            }
        ]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        """Handle tool calls"""
        if name == "ask_about_companies":
            return await self.ask_about_companies(arguments)
        else:
            return [{"type": "text", "text": f"Unknown tool: {name}"}]
    
    async def ask_about_companies(self, arguments: Dict[str, Any]):
        """Use LLM to convert English question to SQL and get results"""
        question = arguments.get("question", "")
        
        # Use LLM to convert question to SQL
        if self.llm_available:
            sql_query = await self.llm_to_sql(question)
        else:
            sql_query = self.fallback_to_sql(question)
        
        try:
            # Run the query
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(sql_query)
            
            # Get results
            columns = [description[0] for description in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            
            # Format the answer
            if len(results) == 0:
                answer = f"SQL Query: {sql_query}\n\nNo results found."
            else:
                answer = f"SQL Query: {sql_query}\n\nFound {len(results)} results:\n{json.dumps(results, indent=2)}"
            
            return [{"type": "text", "text": answer}]
            
        except Exception as e:
            return [{"type": "text", "text": f"Error: {e}\nSQL: {sql_query}"}]
    
    async def llm_to_sql(self, question: str) -> str:
        """Use OpenAI LLM to convert natural language to SQL"""
        try:
            # Create a prompt that includes the database schema
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
            
            # Clean up the response (remove any markdown formatting)
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            
            return sql_query.strip()
            
        except Exception as e:
            print(f"LLM error: {e}")
            return self.fallback_to_sql(question)
    
    def fallback_to_sql(self, question: str) -> str:
        """Fallback pattern matching if LLM is not available"""
        question_lower = question.lower()
        
        # Simple patterns as fallback
        if "list" in question_lower and "companies" in question_lower:
            return 'SELECT "CompanyName", " CompanyNumber", "CompanyStatus" FROM companies LIMIT 10'
        elif "count" in question_lower and "companies" in question_lower:
            return "SELECT COUNT(*) as total_companies FROM companies"
        elif "active" in question_lower and "companies" in question_lower:
            return 'SELECT "CompanyName", " CompanyNumber" FROM companies WHERE "CompanyStatus" = "Active" LIMIT 10'
        elif "micro" in question_lower and "entity" in question_lower:
            return 'SELECT "CompanyName", " CompanyNumber", "Accounts.AccountCategory" FROM companies WHERE "Accounts.AccountCategory" = "MICRO ENTITY" LIMIT 10'
        else:
            return 'SELECT "CompanyName", " CompanyNumber", "CompanyStatus" FROM companies LIMIT 5'

async def main():
    """Start the server"""
    server = LLMMCPServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="llm-companies-server",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(
                    notification_options={},
                    experimental_capabilities={}
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main()) 