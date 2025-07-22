"""
FastAPI wrapper for PubMed MCP Server
Exposes MCP tools as REST API endpoints with OpenAPI 3.0 specifications
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import os
from dotenv import load_dotenv

# Import your existing MCP server
from server import PubMedMCPServer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pubmed-api")

# Initialize FastAPI app
app = FastAPI(
    title="PubMed Research API",
    description="""
    A REST API for searching and retrieving scientific publications from PubMed.
    
    This API wraps the PubMed MCP Server to provide easy access to scientific literature
    for research, AI agents, and automated systems.
    
    ## Features
    
    - 🔍 **Search Publications** - Find scientific papers by keywords, authors, or topics
    - 📄 **Publication Details** - Get comprehensive information about specific papers
    - 🔗 **Similar Articles** - Discover related research papers
    - 📊 **OpenAPI 3.0** - Fully documented API with interactive documentation
    - 🤖 **AI Agent Ready** - Perfect for Azure Foundry and other AI systems
    
    ## Authentication
    
    While not required, providing a PubMed API key will improve rate limits and performance.
    Set your `PUBMED_API_KEY` and `PUBMED_EMAIL` environment variables.
    
    ## Rate Limits
    
    Please be respectful of PubMed's servers. Without an API key, requests are limited to 3/second.
    With an API key, you can make up to 10 requests/second.
    """,
    version="1.0.0",
    contact={
        "name": "PubMed Research API",
        "url": "https://github.com/brown-tech-info/PubMed-MCP---UB",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MCP server
mcp_server = PubMedMCPServer()

# Pydantic models for request/response
class PubMedSearchRequest(BaseModel):
    """Request model for PubMed search"""
    query: str = Field(
        ..., 
        description="Search query for PubMed",
        example="machine learning medicine",
        min_length=1,
        max_length=500
    )
    max_results: int = Field(
        10, 
        ge=1, 
        le=50, 
        description="Maximum number of results to return (1-50)",
        example=10
    )
    sort: str = Field(
        "relevance", 
        description="Sort order for results",
        example="relevance"
    )
    date_range: str = Field(
        "", 
        description="Date range filter (e.g., '2020:2024', 'last_5_years', 'last_year')",
        example="2020:2024"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "artificial intelligence healthcare",
                "max_results": 15,
                "sort": "pub_date", 
                "date_range": "2022:2024"
            }
        }

class PublicationDetailsRequest(BaseModel):
    """Request model for publication details"""
    pmid: str = Field(
        ..., 
        description="PubMed ID (PMID) of the publication",
        example="35000000",
        pattern=r"^\d+$"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "pmid": "35000000"
            }
        }

class SimilarArticlesRequest(BaseModel):
    """Request model for similar articles"""
    pmid: str = Field(
        ..., 
        description="PubMed ID (PMID) of the reference publication",
        example="35000000",
        pattern=r"^\d+$"
    )
    max_results: int = Field(
        10, 
        ge=1, 
        le=20, 
        description="Maximum number of similar articles to return (1-20)",
        example=10
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "pmid": "35000000",
                "max_results": 15
            }
        }

class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[str] = Field(None, description="Response data (markdown formatted)")
    error: Optional[str] = Field(None, description="Error message if request failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current timestamp")
    environment: Dict[str, Any] = Field(..., description="Environment information")

class ToolInfo(BaseModel):
    """Tool information model"""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters schema")

class ToolsResponse(BaseModel):
    """Tools listing response model"""
    success: bool = Field(..., description="Whether the request was successful")
    tools: List[ToolInfo] = Field(..., description="Available tools")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error occurred",
            "metadata": {"type": type(exc).__name__}
        }
    )

@app.get("/", response_model=Dict[str, str], tags=["Health"])
async def root():
    """
    Root endpoint - Basic API information
    
    Returns basic information about the PubMed Research API.
    """
    return {
        "message": "PubMed Research API is running",
        "status": "healthy",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Comprehensive health check endpoint
    
    Returns detailed health information about the service including:
    - Service status
    - Environment configuration
    - API version
    - Timestamp
    """
    from datetime import datetime
    
    return HealthResponse(
        status="healthy",
        service="PubMed Research API",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        environment={
            "has_api_key": bool(os.getenv("PUBMED_API_KEY")),
            "has_email": bool(os.getenv("PUBMED_EMAIL")),
            "tool_name": os.getenv("PUBMED_TOOL_NAME", "PubMedMCPServer"),
            "port": os.getenv("PORT", "8000")
        }
    )

@app.post("/search", response_model=APIResponse, tags=["Search"])
async def search_pubmed(request: PubMedSearchRequest):
    """
    Search PubMed for scientific publications
    
    Searches the PubMed database for scientific publications based on your query.
    Supports advanced search features including:
    
    - **Keywords**: Search by topic, disease, treatment, etc.
    - **Authors**: Use 'author:lastname' format
    - **Date Filtering**: Specify publication date ranges
    - **Sorting**: Order by relevance, date, author, or journal
    
    ## Examples
    
    **Basic search:**
    ```json
    {
        "query": "cancer treatment",
        "max_results": 10
    }
    ```
    
    **Advanced search:**
    ```json
    {
        "query": "machine learning medicine",
        "max_results": 20,
        "sort": "pub_date",
        "date_range": "2020:2024"
    }
    ```
    
    **Author search:**
    ```json
    {
        "query": "author:smith coronavirus",
        "max_results": 15
    }
    ```
    """
    try:
        # Validate sort parameter
        valid_sorts = ["relevance", "pub_date", "author", "journal"]
        if request.sort not in valid_sorts:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort parameter. Must be one of: {', '.join(valid_sorts)}"
            )
        
        result = await mcp_server._search_pubmed(request.dict())
        
        return APIResponse(
            success=True,
            data=result[0].text,
            metadata={
                "query": request.query,
                "max_results": request.max_results,
                "sort": request.sort,
                "date_range": request.date_range
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@app.post("/publication", response_model=APIResponse, tags=["Publications"])
async def get_publication_details(request: PublicationDetailsRequest):
    """
    Get detailed information about a specific publication
    
    Retrieves comprehensive details about a scientific publication using its PubMed ID (PMID).
    
    ## Returns
    
    - **Title** and **Abstract**
    - **Authors** and **Journal** information
    - **Publication date** and **DOI**
    - **Keywords** and **MeSH terms**
    - **Direct links** to PubMed and publisher
    
    ## Example
    
    ```json
    {
        "pmid": "35000000"
    }
    ```
    
    ## Finding PMIDs
    
    You can find PMIDs by:
    1. Using the `/search` endpoint
    2. Looking at PubMed URLs (e.g., pubmed.ncbi.nlm.nih.gov/35000000/)
    3. Citations that include PMID numbers
    """
    try:
        # Validate PMID format
        if not request.pmid.isdigit():
            raise HTTPException(
                status_code=400,
                detail="PMID must be a numeric string (e.g., '35000000')"
            )
        
        result = await mcp_server._get_publication_details(request.dict())
        
        return APIResponse(
            success=True,
            data=result[0].text,
            metadata={
                "pmid": request.pmid,
                "request_type": "publication_details"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Publication details error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve publication details: {str(e)}"
        )

@app.post("/similar", response_model=APIResponse, tags=["Search"])
async def get_similar_articles(request: SimilarArticlesRequest):
    """
    Find articles similar to a given publication
    
    Discovers scientific publications that are related to a reference paper using PubMed's
    sophisticated similarity algorithms.
    
    ## How It Works
    
    PubMed finds similar articles based on:
    - **Shared keywords** and **MeSH terms**
    - **Author connections** and **citation patterns**
    - **Topic similarity** and **research domains**
    
    ## Example
    
    ```json
    {
        "pmid": "35000000",
        "max_results": 15
    }
    ```
    
    ## Use Cases
    
    - **Literature review**: Find related papers for comprehensive research
    - **Discovery**: Explore new research in your field
    - **Citation building**: Find papers to cite in your work
    - **Trend analysis**: See how research topics evolve
    """
    try:
        # Validate PMID format
        if not request.pmid.isdigit():
            raise HTTPException(
                status_code=400,
                detail="PMID must be a numeric string (e.g., '35000000')"
            )
        
        result = await mcp_server._get_similar_articles(request.dict())
        
        return APIResponse(
            success=True,
            data=result[0].text,
            metadata={
                "reference_pmid": request.pmid,
                "max_results": request.max_results,
                "request_type": "similar_articles"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar articles error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find similar articles: {str(e)}"
        )

@app.get("/tools", response_model=ToolsResponse, tags=["Tools"])
async def list_available_tools():
    """
    List all available PubMed research tools
    
    Returns information about all available API endpoints and their capabilities.
    Useful for:
    
    - **API discovery**: See what functionality is available
    - **Integration planning**: Understand tool parameters and schemas
    - **Documentation**: Get tool descriptions and requirements
    """
    try:
        tools = await mcp_server.server.list_tools()
        
        tool_info = []
        for tool in tools:
            tool_info.append(ToolInfo(
                name=tool.name,
                description=tool.description,
                parameters=tool.inputSchema.get("properties", {})
            ))
        
        return ToolsResponse(
            success=True,
            tools=tool_info
        )
        
    except Exception as e:
        logger.error(f"List tools error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list tools: {str(e)}"
        )

# Custom OpenAPI schema modifications
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = app.openapi()
    
    # Add additional metadata
    openapi_schema["info"]["x-api-id"] = "pubmed-research-api"
    openapi_schema["info"]["x-audience"] = "researchers, ai-agents, developers"
    
    # Add server information
    openapi_schema["servers"] = [
        {
            "url": "/",
            "description": "Current deployment"
        }
    ]
    
    # Add tags metadata
    openapi_schema["tags"] = [
        {
            "name": "Health",
            "description": "Service health and status endpoints"
        },
        {
            "name": "Search", 
            "description": "Search and discovery endpoints"
        },
        {
            "name": "Publications",
            "description": "Publication details and information"
        },
        {
            "name": "Tools",
            "description": "API capabilities and tool information"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting PubMed Research API on {host}:{port}")
    logger.info(f"API Documentation: http://{host}:{port}/docs")
    logger.info(f"OpenAPI Spec: http://{host}:{port}/openapi.json")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        log_level="info",
        reload=False  # Set to True for development
    )
