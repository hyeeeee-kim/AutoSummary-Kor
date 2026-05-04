"""Web scraping - DBLP"""
import yaml
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from config.settings import SCRAPER_TIMEOUT, SCRAPER_RETRIES, NUM_WORKERS, ABSTRACT_WORKERS

@dataclass
class Paper:
    title: str
    abstract: str
    source: str
    link: Optional[str] = None

class Scraper:
    def __init__(self, config: Dict):
        self.name = config["name"]
        self.url = config["url"]
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    def _fetch(self, url: str) -> Optional[str]:
        for attempt in range(SCRAPER_RETRIES):
            try:
                return self.session.get(url, timeout=SCRAPER_TIMEOUT).text
            except:
                if attempt == SCRAPER_RETRIES - 1:
                    return None

    def _get_arxiv_link(self, detail_url: str) -> str:
        """Extract arXiv PDF link from DBLP detail page"""
        if not detail_url:
            return ""
        try:
            html = self._fetch(detail_url)
            if not html:
                return ""
            soup = BeautifulSoup(html, "html.parser")
            # Look for arXiv links
            for link in soup.select("a[href*='arxiv']"):
                href = link.get("href", "")
                if "arxiv.org" in href:
                    # Convert to PDF URL
                    if href.endswith(".pdf"):
                        return href
                    elif "arxiv.org/abs/" in href:
                        arxiv_id = href.split("/abs/")[-1]
                        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            return ""
        except:
            return ""

    def _get_abstract(self, url: str) -> str:
        """Fetch abstract from URL (called in parallel)"""
        if not url or not url.startswith("http"):
            return ""
        try:
            html = self._fetch(url)
            if not html:
                return ""
            soup = BeautifulSoup(html, "html.parser")
            for selector in [".abstract", ".tldr-abstract", "meta[name='description']"]:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get("content") if selector.startswith("meta") else elem.get_text(strip=True)
                    if text:
                        return text.strip()
        except:
            pass
        return ""
    
    def _fetch_abstracts_parallel(self, urls: List[Tuple[str, str]]) -> Dict[str, str]:
        """Fetch multiple abstracts in parallel"""
        results = {}
        with ThreadPoolExecutor(max_workers=ABSTRACT_WORKERS) as executor:
            futures = {executor.submit(self._get_abstract, url): link_url for url, link_url in urls}
            for future in as_completed(futures):
                results[futures[future]] = future.result()
        return results

    def scrape(self) -> List[Paper]:
        print(f"    Fetching: {self.url}")
        html = self._fetch(self.url)
        if not html:
            print(f"    FAILED: Could not fetch")
            return []
        
        soup = BeautifulSoup(html, "html.parser")
        elements = soup.select("li[id]")
        
        if not elements:
            for sel in ["dt", "div.entry", "article"]:
                elements = soup.select(sel)
                if elements:
                    break
        
        # Collect all URLs first
        url_list = []
        papers_data = []
        for elem in elements:
            try:
                title_elem = elem.select_one("span.title") or elem.select_one("strong") or elem.select_one("a")
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if not title:
                    continue
                
                link_elem = elem.select_one("a[href]")
                detail_url = link_elem["href"] if link_elem else None
                
                if detail_url and not detail_url.startswith("http"):
                    detail_url = urljoin("https://dblp.org/", detail_url)
                
                # Priority: arXiv PDF > DBLP page link > nothing
                pdf_link = self._get_arxiv_link(detail_url) if detail_url else ""
                final_link = pdf_link or detail_url  # Use arXiv if found, else DBLP page
                
                papers_data.append({"title": title, "url": detail_url, "pdf_link": final_link})
                if detail_url:
                    url_list.append((detail_url, detail_url))
            except:
                pass
        
        # Fetch all abstracts in parallel
        abstracts_map = self._fetch_abstracts_parallel(url_list) if url_list else {}
        
        # Build papers with abstracts
        papers = []
        for p_data in papers_data:
            abstract = abstracts_map.get(p_data["url"], "") if p_data["url"] else ""
            papers.append(Paper(title=p_data["title"], abstract=abstract, source=self.name, link=p_data["pdf_link"]))
        
        print(f"    OK: {len(papers)} papers")
        return papers

class ConferenceScraper:
    def __init__(self, config_path: str = "config/conferences.yaml"):
        with open(config_path) as f:
            config = yaml.safe_load(f)
        self.conferences = {n: c for n, c in config.get("conferences", {}).items() if c.get("enabled")}

    def scrape_all_enabled(self) -> Dict[str, List[Paper]]:
        results = {}
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = {executor.submit(Scraper(c).scrape): n for n, c in self.conferences.items()}
            for future in tqdm(as_completed(futures), total=len(futures), desc="  Scraping"):
                results[futures[future]] = future.result()
        return results
