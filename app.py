"""
FastAPI wrapper for PubMed MCP Server - Azure Foundry Compatible
Exposes MCP tools as REST API endpoints with OpenAPI 3.0 specifications
"""

import asyncio
import logging
import httpx
import xmltodict
from typing import Any, Dict, List, Optional, Union
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pubmed-api")

# Initialize FastAPI app - Azure Foundry Compatible
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
    
    Anonymous access supported for public research use.
    
    ## Rate Limits
    
    - Without API key: 3 requests per second
    - With API key: 10 requests per second
    """,
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simplified PubMed Client (without MCP dependencies)
class SimplePubMedClient:
    def __init__(self):
        self.api_key = os.getenv("PUBMED_API_KEY", "")
        self.email = os.getenv("PUBMED_EMAIL", "")
        self.tool_name = os.getenv("PUBMED_TOOL_NAME", "PubMedAPIClient")
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request to PubMed"""
        common_params = {"retmode": "xml", "retmax": "50"}
        
        if self.api_key:
            common_params["api_key"] = self.api_key
        if self.email:
            common_params["email"] = self.email
        if self.tool_name:
            common_params["tool"] = self.tool_name
            
        final_params = {**common_params, **params}
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=final_params)
                response.raise_for_status()
                
                xml_data = response.text
                parsed_data = xmltodict.parse(xml_data)
                return parsed_data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"PubMed API error: {e}")
            raise HTTPException(status_code=500, detail=f"PubMed API error: {e}")
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise HTTPException(status_code=500, detail=f"Request failed: {e}")
    
    async def search_pubmed(self, query: str, max_results: int = 10) -> str:
        """Search PubMed for publications"""
        try:
            # First, search for PMIDs
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": str(max_results),
                "sort": "relevance"
            }
            
            search_result = await self._make_request("esearch.fcgi", search_params)
            
            if "eSearchResult" not in search_result:
                return "No search results found."
            
            id_list = search_result["eSearchResult"].get("IdList", {}).get("Id", [])
            if not id_list:
                return "No publications found for your query."
            
            # Ensure id_list is a list
            if isinstance(id_list, str):
                id_list = [id_list]
            
            # Get detailed information for found PMIDs
            pmids = ",".join(id_list[:max_results])
            summary_params = {
                "db": "pubmed",
                "id": pmids,
                "rettype": "abstract"
            }
            
            summary_result = await self._make_request("efetch.fcgi", summary_params)
            
            # Format results
            results = []
            articles = summary_result.get("PubmedArticleSet", {}).get("PubmedArticle", [])
            if isinstance(articles, dict):
                articles = [articles]
            
            for i, article in enumerate(articles[:max_results]):
                try:
                    medline = article["MedlineCitation"]
                    pmid = medline["PMID"]["#text"]
                    article_data = medline["Article"]
                    
                    title = article_data.get("ArticleTitle", "No title available")
                    if isinstance(title, dict):
                        title = title.get("#text", "No title available")
                    
                    authors = []
                    author_list = article_data.get("AuthorList", {}).get("Author", [])
                    if isinstance(author_list, dict):
                        author_list = [author_list]
                    
                    for author in author_list[:3]:  # First 3 authors
                        if isinstance(author, dict):
                            lastname = author.get("LastName", "")
                            forename = author.get("ForeName", "")
                            if lastname:
                                authors.append(f"{lastname}, {forename}")
                    
                    journal = article_data.get("Journal", {}).get("Title", "Unknown journal")
                    if isinstance(journal, dict):
                        journal = journal.get("#text", "Unknown journal")
                    
                    pub_date = article_data.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
                    year = pub_date.get("Year", "Unknown year")
                    if isinstance(year, dict):
                        year = year.get("#text", "Unknown year")
                    
                    abstract = article_data.get("Abstract", {}).get("AbstractText", "No abstract available")
                    if isinstance(abstract, dict):
                        abstract = abstract.get("#text", "No abstract available")
                    elif isinstance(abstract, list):
                        abstract = " ".join([a.get("#text", "") if isinstance(a, dict) else str(a) for a in abstract])
                    
                    results.append(f"""
**{i+1}. {title}**
- **PMID**: {pmid}
- **Authors**: {', '.join(authors) if authors else 'Not specified'}
- **Journal**: {journal}
- **Year**: {year}
- **Abstract**: {abstract[:300]}{'...' if len(str(abstract)) > 300 else ''}
- **PubMed URL**: https://pubmed.ncbi.nlm.nih.gov/{pmid}/
""")
                
                except Exception as e:
                    logger.error(f"Error processing article: {e}")
                    continue
            
            if not results:
                return "No valid publications found."
            
            return f"Found {len(results)} publications:\n" + "\n".join(results)
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise HTTPException(status_code=500, detail=f"Search failed: {e}")
    
    async def get_publication_details(self, pmid: str) -> str:
        """Get detailed publication information"""
        try:
            params = {
                "db": "pubmed",
                "id": pmid,
                "rettype": "abstract"
            }
            
            result = await self._make_request("efetch.fcgi", params)
            
            articles = result.get("PubmedArticleSet", {}).get("PubmedArticle", [])
            if isinstance(articles, dict):
                articles = [articles]
            
            if not articles:
                return f"No publication found for PMID: {pmid}"
            
            article = articles[0]
            medline = article["MedlineCitation"]
            article_data = medline["Article"]
            
            title = article_data.get("ArticleTitle", "No title available")
            if isinstance(title, dict):
                title = title.get("#text", "No title available")
            
            # Get full author list
            authors = []
            author_list = article_data.get("AuthorList", {}).get("Author", [])
            if isinstance(author_list, dict):
                author_list = [author_list]
            
            for author in author_list:
                if isinstance(author, dict):
                    lastname = author.get("LastName", "")
                    forename = author.get("ForeName", "")
                    if lastname:
                        authors.append(f"{lastname}, {forename}")
            
            journal = article_data.get("Journal", {}).get("Title", "Unknown journal")
            if isinstance(journal, dict):
                journal = journal.get("#text", "Unknown journal")
            
            pub_date = article_data.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
            year = pub_date.get("Year", "Unknown year")
            if isinstance(year, dict):
                year = year.get("#text", "Unknown year")
            
            abstract = article_data.get("Abstract", {}).get("AbstractText", "No abstract available")
            if isinstance(abstract, dict):
                abstract = abstract.get("#text", "No abstract available")
            elif isinstance(abstract, list):
                abstract = " ".join([a.get("#text", "") if isinstance(a, dict) else str(a) for a in abstract])
            
            return f"""
**Publication Details for PMID: {pmid}**

**Title**: {title}

**Authors**: {', '.join(authors) if authors else 'Not specified'}

**Journal**: {journal}

**Publication Year**: {year}

**Abstract**: {abstract}

**PubMed URL**: https://pubmed.ncbi.nlm.nih.gov/{pmid}/
"""
            
        except Exception as e:
            logger.error(f"Publication details error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get publication details: {e}")
    
    async def get_similar_articles(self, pmid: str, max_results: int = 10) -> str:
        """Get similar articles for a given PMID"""
        try:
            params = {
                "db": "pubmed",
                "id": pmid,
                "retmax": str(max_results),
                "cmd": "neighbor"
            }
            
            result = await self._make_request("elink.fcgi", params)
            
            link_sets = result.get("eLinkResult", {}).get("LinkSet", [])
            if isinstance(link_sets, dict):
                link_sets = [link_sets]
            
            similar_ids = []
            for link_set in link_sets:
                link_set_db = link_set.get("LinkSetDb", [])
                if isinstance(link_set_db, dict):
                    link_set_db = [link_set_db]
                
                for db in link_set_db:
                    if db.get("DbTo") == "pubmed":
                        links = db.get("Link", [])
                        if isinstance(links, dict):
                            links = [links]
                        
                        for link in links:
                            similar_id = link.get("Id")
                            if similar_id and similar_id != pmid:
                                similar_ids.append(similar_id)
            
            if not similar_ids:
                return f"No similar articles found for PMID: {pmid}"
            
            # Get details for similar articles
            pmids = ",".join(similar_ids[:max_results])
            return await self.search_by_pmids(pmids, max_results)
            
        except Exception as e:
            logger.error(f"Similar articles error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get similar articles: {e}")
    
    async def search_by_pmids(self, pmids: str, max_results: int) -> str:
        """Helper method to get publication details for multiple PMIDs"""
        try:
            params = {
                "db": "pubmed",
                "id": pmids,
                "rettype": "abstract"
            }
            
            result = await self._make_request("efetch.fcgi", params)
            
            articles = result.get("PubmedArticleSet", {}).get("PubmedArticle", [])
            if isinstance(articles, dict):
                articles = [articles]
            
            results = []
            for i, article in enumerate(articles[:max_results]):
                try:
                    medline = article["MedlineCitation"]
                    pmid = medline["PMID"]["#text"]
                    article_data = medline["Article"]
                    
                    title = article_data.get("ArticleTitle", "No title available")
                    if isinstance(title, dict):
                        title = title.get("#text", "No title available")
                    
                    results.append(f"**{i+1}. {title}** (PMID: {pmid})")
                
                except Exception as e:
                    logger.error(f"Error processing similar article: {e}")
                    continue
            
            return f"Similar articles:\n" + "\n".join(results)
            
        except Exception as e:
            logger.error(f"Search by PMIDs error: {e}")
            return f"Error retrieving similar articles: {e}"

# Request Models - Pydantic V2 compatible
class PubMedSearchRequest(BaseModel):
    """Request model for PubMed search"""
    query: str = Field(
        ..., 
        description="Search query for PubMed articles",
        min_length=1,
        max_length=500
    )
    max_results: int = Field(
        10, 
        description="Maximum number of results to return",
        ge=1,
        le=100
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "COVID-19 vaccine efficacy",
                "max_results": 10
            }
        }
    }

class PublicationDetailsRequest(BaseModel):
    """Request model for getting publication details"""
    pmid: str = Field(
        ..., 
        description="PubMed ID of the publication",
        pattern=r"^\d+$"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "pmid": "35000000"
            }
        }
    }

class SimilarArticlesRequest(BaseModel):
    """Request model for finding similar articles"""
    pmid: str = Field(
        ..., 
        description="PubMed ID of the reference publication",
        pattern=r"^\d+$"
    )
    max_results: int = Field(
        10, 
        description="Maximum number of similar articles to return",
        ge=1,
        le=50
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "pmid": "35000000",
                "max_results": 10
            }
        }
    }

# Response Models
class SimpleAPIResponse(BaseModel):
    """Simplified API response model"""
    success: bool = Field(..., description="Whether the request was successful")
    data: str = Field(..., description="Response data in markdown format")
    
class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current timestamp")

# Initialize the PubMed client
pubmed_client = SimplePubMedClient()

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error occurred"
        }
    )

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - Basic API information"""
    return {
        "name": "PubMed Research API",
        "version": "1.0.0",
        "description": "REST API for PubMed scientific publications",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="PubMed Research API",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )

@app.post("/search", response_model=SimpleAPIResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}, tags=["Search"])
async def search_publications(request: PubMedSearchRequest):
    """
    Search for publications in PubMed
    
    This endpoint allows you to search for scientific publications using keywords,
    author names, topics, or any other PubMed-supported search terms.
    """
    try:
        result = await pubmed_client.search_pubmed(request.query, request.max_results)
        
        return SimpleAPIResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": f"Search failed: {str(e)}"
            }
        )

@app.post("/publication", response_model=SimpleAPIResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}, tags=["Publications"])
async def get_publication_details(request: PublicationDetailsRequest):
    """
    Get detailed information about a specific publication
    
    Retrieve comprehensive details about a scientific publication using its PubMed ID (PMID).
    """
    try:
        result = await pubmed_client.get_publication_details(request.pmid)
        
        return SimpleAPIResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        logger.error(f"Publication details error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": f"Failed to get publication details: {str(e)}"
            }
        )

@app.post("/similar", response_model=SimpleAPIResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}, tags=["Similar"])
async def get_similar_articles(request: SimilarArticlesRequest):
    """
    Find articles similar to a given publication
    
    Discover publications related to a specific paper using PubMed's similar articles feature.
    """
    try:
        result = await pubmed_client.get_similar_articles(request.pmid, request.max_results)
        
        return SimpleAPIResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        logger.error(f"Similar articles error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": f"Failed to get similar articles: {str(e)}"
            }
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)