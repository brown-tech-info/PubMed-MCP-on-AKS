#!/usr/bin/env python3
"""
PubMed MCP Server

A Model Context Protocol server that provides access to PubMed scientific publications.
This server allows searching for research papers, retrieving abstracts, and getting
publication details from the PubMed database.

Based on:
- MCP Protocol: https://spec.modelcontextprotocol.io/
- PubMed API: https://www.ncbi.nlm.nih.gov/books/NBK25497/
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import httpx
import xmltodict
from dotenv import load_dotenv

# MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pubmed-mcp")


class PubMedMCPServer:
    def __init__(self):
        self.server = Server("pubmed-mcp")
        self.api_key = os.getenv("PUBMED_API_KEY", "")
        self.email = os.getenv("PUBMED_EMAIL", "")
        self.tool_name = os.getenv("PUBMED_TOOL_NAME", "PubMedMCPServer")
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        
        # Setup handlers
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="search_pubmed",
                    description="Search PubMed for scientific publications using keywords, authors, or topics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for PubMed. Examples: 'cancer treatment', 'machine learning medicine', 'author:smith coronavirus'"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return (1-50)",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50
                            },
                            "sort": {
                                "type": "string",
                                "description": "Sort order for results",
                                "enum": ["relevance", "pub_date", "author", "journal"],
                                "default": "relevance"
                            },
                            "date_range": {
                                "type": "string",
                                "description": "Date range filter. Examples: '2020:2024', '2023', 'last_5_years', 'last_year'",
                                "default": ""
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_publication_details",
                    description="Get detailed information about a specific publication by PMID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pmid": {
                                "type": "string",
                                "description": "PubMed ID (PMID) of the publication"
                            }
                        },
                        "required": ["pmid"]
                    }
                ),
                Tool(
                    name="get_similar_articles",
                    description="Find articles similar to a given publication",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pmid": {
                                "type": "string",
                                "description": "PubMed ID (PMID) of the reference publication"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of similar articles to return (1-20)",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 20
                            }
                        },
                        "required": ["pmid"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
            """Handle tool calls"""
            try:
                if name == "search_pubmed":
                    return await self._search_pubmed(arguments)
                elif name == "get_publication_details":
                    return await self._get_publication_details(arguments)
                elif name == "get_similar_articles":
                    return await self._get_similar_articles(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Error in tool {name}: {str(e)}")
                return [TextContent(
                    type="text",
                    text=f"Error executing {name}: {str(e)}"
                )]

    async def _make_api_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the PubMed E-utilities API with proper error handling"""
        # Common parameters for all E-utilities requests
        common_params = {
            "retmode": "xml",
            "rettype": "abstract"
        }
        
        # Add authentication and identification
        if self.api_key:
            common_params["api_key"] = self.api_key
        if self.email:
            common_params["email"] = self.email
        if self.tool_name:
            common_params["tool"] = self.tool_name
            
        # Merge with request-specific parameters
        final_params = {**common_params, **params}
        url = f"{self.base_url}/{endpoint}"
        
        logger.info(f"Making API request to {endpoint} with params: {list(final_params.keys())}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=final_params)
                response.raise_for_status()
                
                # Parse XML response
                xml_data = response.text
                parsed_data = xmltodict.parse(xml_data)
                
                # Check for API errors
                if "eSearchResult" in parsed_data:
                    error_list = parsed_data["eSearchResult"].get("ErrorList")
                    if error_list:
                        raise Exception(f"PubMed API error: {error_list}")
                
                return parsed_data
                
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.TimeoutException:
            raise Exception("Request timed out - PubMed API may be slow")
        except Exception as e:
            raise Exception(f"API request failed: {str(e)}")

    async def _search_pubmed(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Search PubMed for publications with enhanced query building"""
        query = arguments["query"]
        max_results = arguments.get("max_results", 10)
        sort_order = arguments.get("sort", "relevance")
        date_range = arguments.get("date_range", "")
        
        # Build enhanced search query
        search_query = query
        
        # Handle date range filtering
        if date_range:
            current_year = datetime.now().year
            if date_range == "last_5_years":
                search_query += f" AND {current_year-5}:{current_year}[pdat]"
            elif date_range == "last_year":
                search_query += f" AND {current_year-1}:{current_year}[pdat]"
            elif ":" in date_range:
                search_query += f" AND {date_range}[pdat]"
            elif date_range.isdigit() and len(date_range) == 4:
                search_query += f" AND {date_range}[pdat]"
        
        try:
            # Step 1: Search for PMIDs using esearch
            search_params = {
                "db": "pubmed",
                "term": search_query,
                "retmax": str(max_results),
                "sort": sort_order,
                "usehistory": "y"  # Use history for better performance
            }
            
            search_result = await self._make_api_request("esearch.fcgi", search_params)
            
            # Extract PMIDs and search metadata
            pmids = []
            total_count = 0
            
            if "eSearchResult" in search_result:
                search_data = search_result["eSearchResult"]
                total_count = int(search_data.get("Count", 0))
                
                id_list = search_data.get("IdList", {})
                if id_list and "Id" in id_list:
                    pmid_data = id_list["Id"]
                    if isinstance(pmid_data, list):
                        pmids = pmid_data
                    else:
                        pmids = [pmid_data] if pmid_data else []
            
            if not pmids:
                return [TextContent(
                    type="text",
                    text=f"No publications found for query: '{query}'\n\nTry:\n- Different keywords\n- Broader search terms\n- Removing date filters"
                )]
            
            # Step 2: Fetch detailed information using efetch
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "rettype": "abstract",
                "retmode": "xml"
            }
            
            fetch_result = await self._make_api_request("efetch.fcgi", fetch_params)
            
            # Step 3: Parse and format results
            articles = self._parse_articles(fetch_result)
            
            if not articles:
                return [TextContent(
                    type="text",
                    text="Found PMIDs but couldn't retrieve article details. The articles may be restricted or unavailable."
                )]
            
            # Format comprehensive response
            response_parts = [
                f"# PubMed Search Results\n",
                f"**Query:** {query}",
                f"**Total matches:** {total_count:,}",
                f"**Showing:** {len(articles)} results",
                f"**Sort order:** {sort_order}"
            ]
            
            if date_range:
                response_parts.append(f"**Date filter:** {date_range}")
            
            response_parts.append("\n---\n")
            
            # Add each article
            for i, article in enumerate(articles, 1):
                article_text = self._format_article_summary(article, i)
                response_parts.append(article_text)
                response_parts.append("---\n")
            
            return [TextContent(type="text", text="\n".join(response_parts))]
            
        except Exception as e:
            logger.error(f"Error searching PubMed: {str(e)}")
            return [TextContent(
                type="text",
                text=f"Search failed: {str(e)}\n\nPlease check:\n- Your internet connection\n- Query syntax\n- Try a simpler search term"
            )]

    async def _get_publication_details(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Get comprehensive details for a specific publication"""
        pmid = arguments["pmid"].strip()
        
        # Validate PMID format
        if not pmid.isdigit():
            return [TextContent(
                type="text",
                text=f"Invalid PMID format: '{pmid}'. PMID should be a number (e.g., '12345678')"
            )]
        
        try:
            fetch_params = {
                "db": "pubmed",
                "id": pmid,
                "rettype": "abstract",
                "retmode": "xml"
            }
            
            result = await self._make_api_request("efetch.fcgi", fetch_params)
            articles = self._parse_articles(result)
            
            if not articles:
                return [TextContent(
                    type="text",
                    text=f"No publication found with PMID: {pmid}\n\nThis could mean:\n- The PMID doesn't exist\n- The article is not in PubMed\n- There's a temporary access issue"
                )]
            
            article = articles[0]
            response_text = self._format_article_details(article)
            
            return [TextContent(type="text", text=response_text)]
            
        except Exception as e:
            logger.error(f"Error fetching publication details for PMID {pmid}: {str(e)}")
            return [TextContent(
                type="text",
                text=f"Failed to retrieve details for PMID {pmid}: {str(e)}"
            )]

    async def _get_similar_articles(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Find articles similar to a given publication using PubMed's related articles feature"""
        pmid = arguments["pmid"].strip()
        max_results = arguments.get("max_results", 10)
        
        # Validate PMID
        if not pmid.isdigit():
            return [TextContent(
                type="text",
                text=f"Invalid PMID format: '{pmid}'. PMID should be a number."
            )]
        
        try:
            # Use elink to find related articles
            link_params = {
                "dbfrom": "pubmed",
                "db": "pubmed",
                "id": pmid,
                "linkname": "pubmed_pubmed",
                "retmax": str(max_results + 1)  # +1 because original article might be included
            }
            
            link_result = await self._make_api_request("elink.fcgi", link_params)
            
            # Extract linked PMIDs
            similar_pmids = []
            if "eLinkResult" in link_result and "LinkSet" in link_result["eLinkResult"]:
                linkset = link_result["eLinkResult"]["LinkSet"]
                if isinstance(linkset, list):
                    linkset = linkset[0] if linkset else {}
                
                if "LinkSetDb" in linkset:
                    linksetdb = linkset["LinkSetDb"]
                    if isinstance(linksetdb, list):
                        linksetdb = linksetdb[0] if linksetdb else {}
                    
                    if "Link" in linksetdb:
                        links = linksetdb["Link"]
                        if isinstance(links, list):
                            # Exclude the original PMID from similar articles
                            similar_pmids = [link["Id"] for link in links if link["Id"] != pmid]
                        else:
                            if links["Id"] != pmid:
                                similar_pmids = [links["Id"]]
            
            if not similar_pmids:
                return [TextContent(
                    type="text",
                    text=f"No similar articles found for PMID {pmid}.\n\nThis could mean:\n- The article is very specialized\n- It's a very new publication\n- The article is not well-connected in the literature"
                )]
            
            # Limit results as requested
            similar_pmids = similar_pmids[:max_results]
            
            # Fetch details for similar articles
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(similar_pmids),
                "rettype": "abstract",
                "retmode": "xml"
            }
            
            fetch_result = await self._make_api_request("efetch.fcgi", fetch_params)
            articles = self._parse_articles(fetch_result)
            
            if not articles:
                return [TextContent(
                    type="text",
                    text=f"Found similar article IDs but couldn't retrieve details for PMID {pmid}"
                )]
            
            # Format response
            response_parts = [
                f"# Similar Articles to PMID {pmid}\n",
                f"**Found:** {len(articles)} similar articles\n",
                "---\n"
            ]
            
            for i, article in enumerate(articles, 1):
                article_text = self._format_article_summary(article, i)
                response_parts.append(article_text)
                response_parts.append("---\n")
            
            return [TextContent(type="text", text="\n".join(response_parts))]
            
        except Exception as e:
            logger.error(f"Error finding similar articles for PMID {pmid}: {str(e)}")
            return [TextContent(
                type="text",
                text=f"Failed to find similar articles for PMID {pmid}: {str(e)}"
            )]

    def _parse_articles(self, xml_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse XML data and extract article information with enhanced error handling"""
        articles = []
        
        try:
            pubmed_data = xml_data.get("PubmedArticleSet", {})
            if not pubmed_data:
                logger.warning("No PubmedArticleSet found in XML response")
                return articles
                
            pubmed_articles = pubmed_data.get("PubmedArticle", [])
            if not isinstance(pubmed_articles, list):
                pubmed_articles = [pubmed_articles]
            
            for article_data in pubmed_articles:
                article = self._parse_single_article(article_data)
                if article:
                    articles.append(article)
                    
        except Exception as e:
            logger.error(f"Error parsing articles XML: {str(e)}")
            
        return articles

    def _parse_single_article(self, article_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single article with comprehensive data extraction"""
        try:
            medline_citation = article_data.get("MedlineCitation", {})
            pubmed_data = article_data.get("PubmedData", {})
            
            # Basic article info
            article_info = medline_citation.get("Article", {})
            
            # Extract PMID
            pmid = medline_citation.get("PMID", {})
            if isinstance(pmid, dict):
                pmid = pmid.get("#text", "")
            pmid = str(pmid) if pmid else "Unknown"
            
            # Extract title
            title = article_info.get("ArticleTitle", "")
            if isinstance(title, dict):
                title = title.get("#text", "")
            title = str(title) if title else "No title available"
            
            # Extract authors
            authors = self._extract_authors(article_info.get("AuthorList", {}))
            
            # Extract journal information
            journal_info = article_info.get("Journal", {})
            journal_title = journal_info.get("Title", "Unknown journal")
            journal_iso = journal_info.get("ISOAbbreviation", "")
            
            # Extract publication date
            pub_date = self._extract_pub_date(journal_info.get("JournalIssue", {}))
            
            # Extract abstract
            abstract = self._extract_abstract(article_info.get("Abstract", {}))
            
            # Extract DOI and other identifiers
            doi = self._extract_doi(article_info.get("ELocationID", []))
            
            # Extract keywords
            keywords = self._extract_keywords(medline_citation.get("KeywordList", {}))
            
            # Extract publication types
            pub_types = self._extract_publication_types(article_info.get("PublicationTypeList", {}))
            
            # Extract MeSH terms if available
            mesh_terms = self._extract_mesh_terms(medline_citation.get("MeshHeadingList", {}))
            
            return {
                "pmid": pmid,
                "title": title,
                "authors": authors,
                "journal": journal_title,
                "journal_iso": journal_iso,
                "pub_date": pub_date,
                "abstract": abstract,
                "doi": doi,
                "keywords": keywords,
                "publication_types": pub_types,
                "mesh_terms": mesh_terms
            }
            
        except Exception as e:
            logger.error(f"Error parsing single article: {str(e)}")
            return None

    def _extract_authors(self, author_list: Dict[str, Any]) -> str:
        """Extract authors with improved formatting"""
        try:
            authors = author_list.get("Author", [])
            if not isinstance(authors, list):
                authors = [authors]
            
            author_names = []
            for author in authors[:15]:  # Limit to first 15 authors
                if isinstance(author, dict):
                    last_name = author.get("LastName", "")
                    fore_name = author.get("ForeName", "")
                    initials = author.get("Initials", "")
                    
                    if last_name:
                        if fore_name:
                            author_names.append(f"{last_name} {fore_name}")
                        elif initials:
                            author_names.append(f"{last_name} {initials}")
                        else:
                            author_names.append(last_name)
            
            if len(authors) > 15:
                return ", ".join(author_names) + ", et al."
            else:
                return ", ".join(author_names) if author_names else "Authors not available"
                
        except Exception:
            return "Authors not available"

    def _extract_pub_date(self, journal_issue: Dict[str, Any]) -> str:
        """Extract publication date with multiple format support"""
        try:
            pub_date = journal_issue.get("PubDate", {})
            if isinstance(pub_date, dict):
                year = pub_date.get("Year", "")
                month = pub_date.get("Month", "")
                day = pub_date.get("Day", "")
                
                # Handle date string format
                date_string = pub_date.get("MedlineDate", "")
                if date_string:
                    return date_string
                
                if year:
                    date_parts = [year]
                    if month:
                        date_parts.append(month)
                        if day:
                            date_parts.append(day)
                    return " ".join(date_parts)
            
            return "Date not available"
            
        except Exception:
            return "Date not available"

    def _extract_abstract(self, abstract_data: Dict[str, Any]) -> str:
        """Extract abstract with support for structured abstracts"""
        try:
            abstract_text = abstract_data.get("AbstractText", "")
            
            if isinstance(abstract_text, list):
                # Handle structured abstracts with labels
                text_parts = []
                for part in abstract_text:
                    if isinstance(part, dict):
                        label = part.get("@Label", "")
                        text = part.get("#text", "")
                        if label and text:
                            text_parts.append(f"**{label}:** {text}")
                        elif text:
                            text_parts.append(text)
                    else:
                        text_parts.append(str(part))
                return "\n\n".join(text_parts)
                
            elif isinstance(abstract_text, dict):
                return abstract_text.get("#text", "")
            else:
                return str(abstract_text) if abstract_text else ""
                
        except Exception:
            return ""

    def _extract_doi(self, elocation_ids: List[Dict[str, Any]]) -> str:
        """Extract DOI with validation"""
        try:
            if not isinstance(elocation_ids, list):
                elocation_ids = [elocation_ids] if elocation_ids else []
            
            for elocation in elocation_ids:
                if isinstance(elocation, dict):
                    id_type = elocation.get("@EIdType", "")
                    if id_type.lower() == "doi":
                        doi = elocation.get("#text", "")
                        if doi:
                            return doi
            
            return ""
            
        except Exception:
            return ""

    def _extract_keywords(self, keyword_list: Dict[str, Any]) -> List[str]:
        """Extract keywords with deduplication"""
        try:
            keywords = keyword_list.get("Keyword", [])
            if not isinstance(keywords, list):
                keywords = [keywords] if keywords else []
            
            keyword_texts = []
            seen_keywords = set()
            
            for keyword in keywords:
                if isinstance(keyword, dict):
                    text = keyword.get("#text", "")
                    if text and text.lower() not in seen_keywords:
                        keyword_texts.append(text)
                        seen_keywords.add(text.lower())
                elif keyword and str(keyword).lower() not in seen_keywords:
                    keyword_texts.append(str(keyword))
                    seen_keywords.add(str(keyword).lower())
            
            return keyword_texts
            
        except Exception:
            return []

    def _extract_publication_types(self, pub_type_list: Dict[str, Any]) -> List[str]:
        """Extract publication types"""
        try:
            pub_types = pub_type_list.get("PublicationType", [])
            if not isinstance(pub_types, list):
                pub_types = [pub_types] if pub_types else []
            
            type_texts = []
            for pub_type in pub_types:
                if isinstance(pub_type, dict):
                    text = pub_type.get("#text", "")
                    if text:
                        type_texts.append(text)
                else:
                    type_texts.append(str(pub_type))
            
            return type_texts
            
        except Exception:
            return []

    def _extract_mesh_terms(self, mesh_list: Dict[str, Any]) -> List[str]:
        """Extract MeSH (Medical Subject Headings) terms"""
        try:
            mesh_headings = mesh_list.get("MeshHeading", [])
            if not isinstance(mesh_headings, list):
                mesh_headings = [mesh_headings] if mesh_headings else []
            
            mesh_terms = []
            for heading in mesh_headings[:10]:  # Limit to first 10 MeSH terms
                if isinstance(heading, dict):
                    descriptor = heading.get("DescriptorName", {})
                    if isinstance(descriptor, dict):
                        term = descriptor.get("#text", "")
                        if term:
                            mesh_terms.append(term)
            
            return mesh_terms
            
        except Exception:
            return []

    def _format_article_summary(self, article: Dict[str, Any], index: int) -> str:
        """Format article for summary display with enhanced clickable links"""
        title = article.get('title', 'No title')
        authors = article.get('authors', 'No authors')
        journal = article.get('journal', 'Unknown journal')
        pub_date = article.get('pub_date', 'Unknown date')
        pmid = article.get('pmid', 'Unknown')
        abstract = article.get('abstract', '')
        doi = article.get('doi', '')
        
        # Truncate abstract for summary
        abstract_preview = ""
        if abstract:
            abstract_clean = abstract.replace('**', '').replace('\n\n', ' ')
            if len(abstract_clean) > 200:
                abstract_preview = f"\n**Abstract:** {abstract_clean[:200]}..."
            else:
                abstract_preview = f"\n**Abstract:** {abstract_clean}"
        
        # Create clickable links section
        links_section = f"\n\n🔗 **Links:**\n• [📄 PubMed](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)"
        
        if doi:
            links_section += f"\n• [📋 DOI](https://doi.org/{doi})"
            links_section += f"\n• [🔍 Full Text](https://doi.org/{doi})"
        
        return f"""## {index}. {title}

**Authors:** {authors}
**Journal:** {journal}
**Published:** {pub_date}
**PMID:** {pmid}{abstract_preview}{links_section}
"""

    def _format_article_details(self, article: Dict[str, Any]) -> str:
        """Format comprehensive article details with enhanced clickable links"""
        pmid = article.get('pmid', 'Unknown')
        title = article.get('title', 'No title')
        authors = article.get('authors', 'No authors')
        journal = article.get('journal', 'Unknown journal')
        journal_iso = article.get('journal_iso', '')
        pub_date = article.get('pub_date', 'Unknown date')
        doi = article.get('doi', '')
        abstract = article.get('abstract', '')
        keywords = article.get('keywords', [])
        pub_types = article.get('publication_types', [])
        mesh_terms = article.get('mesh_terms', [])
        
        details = [
            f"# 📄 Publication Details - PMID {pmid}\n",
            f"## {title}\n",
            f"**Authors:** {authors}\n",
            f"**Journal:** {journal}"
        ]
        
        if journal_iso:
            details.append(f"**Journal (ISO):** {journal_iso}")
        
        details.extend([
            f"**Published:** {pub_date}",
            f"**PMID:** {pmid}"
        ])
        
        # Enhanced links section with emojis and better formatting
        links_section = ["\n## 🔗 Quick Access Links"]
        links_section.append(f"• [📄 **View on PubMed**](https://pubmed.ncbi.nlm.nih.gov/{pmid}/) - Official PubMed page")
        
        if doi:
            details.append(f"**DOI:** {doi}")
            links_section.append(f"• [📋 **DOI Link**](https://doi.org/{doi}) - Publisher's page")
            links_section.append(f"• [🔍 **Full Text Access**](https://doi.org/{doi}) - Try to access full paper")
        else:
            links_section.append(f"• [🔍 **Search Full Text**](https://pubmed.ncbi.nlm.nih.gov/{pmid}/) - Look for free full text")
        
        # Add additional useful links
        links_section.append(f"• [📊 **Citation Analysis**](https://scholar.google.com/scholar?q={pmid}) - Google Scholar citations")
        links_section.append(f"• [🔗 **Find Similar**](https://pubmed.ncbi.nlm.nih.gov/sites/pubmed/?linkname=pubmed_pubmed&from_uid={pmid}) - Related articles")
        
        details.extend(links_section)
        
        if pub_types:
            details.append(f"\n**Publication Types:** {', '.join(pub_types)}")
        
        if abstract:
            details.append(f"\n## 📋 Abstract\n\n{abstract}")
        
        if keywords:
            details.append(f"\n**🏷️ Keywords:** {', '.join(keywords)}")
        
        if mesh_terms:
            details.append(f"\n**🔬 MeSH Terms:** {', '.join(mesh_terms)}")
        
        return "\n".join(details)

    async def run(self):
        """Run the MCP server with proper initialization"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Main entry point"""
    try:
        server = PubMedMCPServer()
        logger.info("Starting PubMed MCP Server...")
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()
