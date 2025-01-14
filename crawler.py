import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import hashlib
from transformers import pipeline
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx
import plotly.graph_objects as go
from collections import defaultdict

# BERT-based embedding pipeline
bert_embedder = pipeline("feature-extraction", model="bert-base-uncased", tokenizer="bert-base-uncased")

class AsyncWebCrawler:
    def __init__(self, config_id):
        from app import db, CrawlConfig
        self.config = CrawlConfig.query.get(config_id)
        if not self.config:
            raise ValueError(f"No crawl configuration found with id {config_id}")
        
        self.base_url = self.config.site.url if self.config.site else self.config.project.client_site_url
        self.visited_urls = set()
        self.session = None
        self.keywords = [k.strip() for k in (self.config.keywords or '').split(',')]
        self.db = db
        self.should_stop = False
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()
        
    def normalize_url(self, url):
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
        
    async def fetch_page(self, url):
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.text()
                return None
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None
            
    def extract_links(self, html, base_url):
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith(('http://', 'https://')):
                absolute_url = href
            else:
                absolute_url = urljoin(base_url, href)
            
            # Normalize URL
            normalized_url = self.normalize_url(absolute_url)
            
            # Check if URL is from same domain
            if urlparse(normalized_url).netloc == urlparse(self.base_url).netloc:
                links.append(normalized_url)
                
        return list(set(links))
        
    def extract_keywords(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        text = ' '.join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])])
        
        # Se não houver keywords configuradas, retornar vazio
        if not self.keywords:
            return ''
            
        # Get BERT embeddings
        embeddings = bert_embedder(text[:512], return_tensors=True)  # Limitar texto para não sobrecarregar
        embeddings = np.mean(embeddings[0], axis=0)
        
        # Compare with keyword embeddings
        keyword_scores = []
        for keyword in self.keywords:
            keyword_embedding = np.mean(bert_embedder(keyword, return_tensors=True)[0], axis=0)
            similarity = cosine_similarity([embeddings], [keyword_embedding])[0][0]
            if similarity > 0.5:  # Threshold fixo por enquanto
                keyword_scores.append(keyword)
                
        return ','.join(keyword_scores)
        
    def compute_content_hash(self, html):
        return hashlib.sha256(html.encode()).hexdigest()
        
    async def crawl_url(self, url, depth=0):
        from app import CrawlResult, CrawlLink
        
        if self.should_stop:
            return None
            
        if depth > self.config.max_depth or url in self.visited_urls:
            return None
            
        print(f"Crawling {url} at depth {depth}")
        self.visited_urls.add(url)
        
        # Respect crawl delay
        await asyncio.sleep(self.config.delay)
        
        try:
            html = await self.fetch_page(url)
            if not html:
                return None
                
            # Extract information
            content_hash = self.compute_content_hash(html)
            keywords = self.extract_keywords(html)
            
            print(f"Found keywords: {keywords}")
            
            # Save result
            result = CrawlResult(
                config_id=self.config.id,
                url=url,
                content_hash=content_hash,
                keywords=keywords
            )
            self.db.session.add(result)
            self.db.session.commit()
            
            # Extract and crawl links
            links = self.extract_links(html, url)
            print(f"Found {len(links)} links")
            
            for link in links:
                if link not in self.visited_urls and len(self.visited_urls) < self.config.max_pages:
                    if self.should_stop:
                        return result
                        
                    # Create link relationship
                    child_result = await self.crawl_url(link, depth + 1)
                    if child_result:
                        link = CrawlLink(source_id=result.id, target_id=child_result.id)
                        self.db.session.add(link)
                        self.db.session.commit()
                        
            return result
            
        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")
            return None
        
    async def run(self):
        from app import CrawlResult
        
        try:
            print(f"Starting crawler for {self.base_url}")
            print(f"Max pages: {self.config.max_pages}")
            print(f"Max depth: {self.config.max_depth}")
            print(f"Keywords: {self.keywords}")
            
            self.config.status = 'running'
            self.db.session.commit()
            
            async with self:
                await self.crawl_url(self.base_url)
                
            if not self.should_stop:
                # Cluster pages based on keywords
                results = CrawlResult.query.filter_by(config_id=self.config.id).all()
                
                if self.keywords and results:
                    keyword_vectors = []
                    for result in results:
                        vector = np.zeros(len(self.keywords))
                        result_keywords = result.keywords.split(',') if result.keywords else []
                        for i, keyword in enumerate(self.keywords):
                            if keyword in result_keywords:
                                vector[i] = 1
                        keyword_vectors.append(vector)
                        
                    if keyword_vectors:
                        # Compute similarity matrix
                        similarity_matrix = cosine_similarity(keyword_vectors)
                        
                        # Create graph
                        G = nx.Graph()
                        for i in range(len(results)):
                            for j in range(i + 1, len(results)):
                                if similarity_matrix[i][j] > 0.5:  # Threshold fixo
                                    G.add_edge(i, j)
                                    
                        # Find clusters
                        clusters = list(nx.connected_components(G))
                        
                        # Assign cluster labels
                        for i, cluster in enumerate(clusters):
                            for node_id in cluster:
                                results[node_id].cluster = f"Cluster {i + 1}"
                                
                        self.db.session.commit()
                
                self.config.status = 'completed'
            else:
                self.config.status = 'stopped'
                
            self.db.session.commit()
            print("Crawler finished")
            
        except Exception as e:
            print(f"Error during crawl: {str(e)}")
            self.config.status = 'error'
            self.db.session.commit()
            raise e

async def run_crawler(config_id):
    try:
        crawler = AsyncWebCrawler(config_id)
        await crawler.run()
    except Exception as e:
        print(f"Error running crawler: {str(e)}")
