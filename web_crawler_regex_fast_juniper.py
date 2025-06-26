#!/usr/bin/env python3
"""
SLUSD Website Crawler - Find pages and PDFs containing "14735 Juniper St"
Crawls www.slusd.us to identify content that needs address updates
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import csv
import time
import re
from collections import deque
import PyPDF2
import io
import os
from datetime import datetime

class SLUSDCrawler:
    def __init__(self, base_url="https://www.slusd.us"):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.visited_urls = set()
        self.found_pages = []
        self.found_pdfs = []
        
        # Define address patterns to search for - multiple patterns for better coverage
        self.address_patterns = [
            r'14735\s*Juniper\s*(?:St\.?|Street)?(?!\w)',   # Comprehensive pattern
            r'14735\s*Juniper\s*St\.?',                     # 14735 Juniper St variations
            r'14735\s*Juniper\s*Street',                    # 14735 Juniper Street
            r'14735\s*Juniper(?!\w)',                       # 14735 Juniper (no street)
            r'14735\s*(?:N\.?\s*)?Juniper\s*(?:St\.?|Street)?', # With North prefix
            r'14735\s*North\s*Juniper\s*(?:St\.?|Street)?', # 14735 North Juniper variations
            r'14735\s*N\s*Juniper(?!\w)',                   # 14735 N Juniper (no punctuation)
        ]
        
        # Compile patterns for better performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.address_patterns]
        
        # URL filters to skip non-content URLs
        self.skip_url_patterns = [
            r'/css/', r'/js/', r'/images/', r'/img/', r'/assets/',
            r'\.css$', r'\.js$', r'\.png$', r'\.jpg$', r'\.jpeg$', r'\.gif$', r'\.ico$',
            r'\.woff$', r'\.woff2$', r'\.ttf$', r'\.eot$', r'\.svg$', r'\.webp$',
            r'/feeds/', r'/rss/', r'/sitemap', r'\.xml$', r'\.json$',
            r'#', r'javascript:', r'mailto:', r'tel:', r'ftp:'
        ]
        self.compiled_skip_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.skip_url_patterns]
        
        # Fast pre-check string for quick elimination
        self.quick_check = '14735'
        
        self.session = requests.Session()
        self.output_file = "slusd_juniper_audit.csv"
        self.progress_file = "crawl_progress_juniper.txt"
        
        # Set headers to appear as a regular browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Initialize CSV file with headers
        self.init_csv_file()

    def init_csv_file(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.output_file):
            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['URL', 'Type', 'Title', 'Address Found', 'Notes', 'Parent Page', 'Timestamp']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

    def append_to_csv(self, result):
        """Append a single result to the CSV file immediately"""
        with open(self.output_file, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['URL', 'Type', 'Title', 'Address Found', 'Notes', 'Parent Page', 'Timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow(result)

    def save_progress(self, pages_crawled, current_url):
        """Save progress to a file"""
        with open(self.progress_file, 'w') as f:
            f.write(f"Pages crawled: {pages_crawled}\n")
            f.write(f"Current URL: {current_url}\n")
            f.write(f"Found pages: {len(self.found_pages)}\n")
            f.write(f"Found PDFs: {len(self.found_pdfs)}\n")
            f.write(f"Last update: {datetime.now()}\n")

    def is_valid_url(self, url):
        """Check if URL is valid and within the target domain"""
        try:
            parsed = urlparse(url)
            return (parsed.netloc == self.domain or parsed.netloc == '' or 
                    parsed.netloc.endswith('.slusd.us'))
        except Exception:
            return False

    def should_skip_url(self, url):
        """Check if URL should be skipped (assets, etc.)"""
        for pattern in self.compiled_skip_patterns:
            if pattern.search(url):
                return True
        return False

    def get_page_content(self, url):
        """Fetch and return page content with better error handling"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Try to detect encoding
            content_type = response.headers.get('content-type', '')
            if 'charset=' in content_type:
                encoding = content_type.split('charset=')[1].split(';')[0].strip()
                response.encoding = encoding
            
            return response.text, content_type
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None, None
        except Exception as e:
            print(f"Unexpected error fetching {url}: {e}")
            return None, None

    def safe_parse_html(self, html_content):
        """Parse HTML with multiple parser fallbacks"""
        parsers = ['html.parser', 'lxml', 'html5lib']
        
        for parser in parsers:
            try:
                return BeautifulSoup(html_content, parser)
            except Exception as e:
                print(f"Parser {parser} failed, trying next...")
                continue
        
        # If all parsers fail, try with error handling
        try:
            # Remove problematic characters and try again
            cleaned_html = re.sub(r'[^\x00-\x7F]+', ' ', html_content)
            return BeautifulSoup(cleaned_html, 'html.parser')
        except Exception as e:
            print(f"All parsers failed: {e}")
            return None

    def extract_links(self, html, base_url):
        """Extract all links from HTML content with better error handling"""
        try:
            soup = self.safe_parse_html(html)
            if not soup:
                return set()
            
            links = set()
            
            # Find all links
            for tag in soup.find_all(['a', 'link'], href=True):
                try:
                    href = tag['href']
                    full_url = urljoin(base_url, href)
                    
                    # Clean up the URL (remove fragments)
                    parsed = urlparse(full_url)
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if parsed.query:
                        clean_url += f"?{parsed.query}"
                    
                    links.add(clean_url)
                except Exception as e:
                    continue  # Skip problematic links
            
            return links
        except Exception as e:
            print(f"Error extracting links: {e}")
            return set()

    def check_address_in_text(self, text):
        """Check if any of the target address patterns are mentioned in text"""
        try:
            if not text:
                return False, None
            
            # Quick pre-check: if '835' isn't in the text, skip expensive regex
            if self.quick_check not in text:
                return False, None
            
            # Check each pattern - return immediately on first match
            for i, pattern in enumerate(self.compiled_patterns):
                match = pattern.search(text)
                if match:
                    return True, match.group()
            
            return False, None
        except Exception:
            return False, None

    def check_pdf_content(self, url):
        """Download and check PDF content for the target address"""
        try:
            # Check file size first to avoid huge downloads
            response = self.session.head(url, timeout=5)
            if response.headers.get('content-length'):
                size_mb = int(response.headers['content-length']) / (1024 * 1024)
                if size_mb > 50:  # Skip PDFs larger than 50MB
                    print(f"Skipping large PDF ({size_mb:.1f}MB): {url}")
                    return False, None
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Read PDF content
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Check each page and return immediately on first match
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    
                    # Quick pre-check before expensive regex
                    if self.quick_check in page_text:
                        found, matched_text = self.check_address_in_text(page_text)
                        if found:
                            return True, matched_text  # Stop as soon as we find a match
                except Exception:
                    continue  # Skip pages that can't be read
            
            return False, None  # No matches found in any page
            
        except Exception as e:
            print(f"Error reading PDF {url}: {e}")
            return False, None

    def record_finding(self, url, content_type, matched_text, title="", notes="", parent_page=""):
        """Record a finding and immediately save to CSV"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        result = {
            'URL': url,
            'Type': content_type,
            'Title': title,
            'Address Found': matched_text,
            'Notes': notes,
            'Parent Page': parent_page,
            'Timestamp': timestamp
        }
        
        # Add to in-memory lists
        if content_type == 'PDF':
            self.found_pdfs.append(result)
        else:
            self.found_pages.append(result)
        
        # Immediately save to CSV
        self.append_to_csv(result)
        
        if parent_page:
            print(f"✓ Found '{matched_text}' in {content_type}: {url} (linked from: {parent_page})")
        else:
            print(f"✓ Found '{matched_text}' in {content_type}: {url}")

    def crawl_site(self, max_pages=5000):
        """Main crawling function with improved error handling"""
        print(f"Starting crawl of {self.base_url}")
        print(f"Looking for pages and PDFs containing address patterns:")
        for i, pattern in enumerate(self.address_patterns, 1):
            print(f"  {i}. {pattern}")
        print(f"Results will be saved continuously to: {self.output_file}")
        
        # Queue for URLs to visit
        url_queue = deque([self.base_url])
        pages_crawled = 0
        
        while url_queue and pages_crawled < max_pages:
            current_url = url_queue.popleft()
            
            if current_url in self.visited_urls:
                continue
                
            self.visited_urls.add(current_url)
            pages_crawled += 1
            
            print(f"Crawling ({pages_crawled}/{max_pages}): {current_url}")
            
            # Save progress every 50 pages
            if pages_crawled % 50 == 0:
                self.save_progress(pages_crawled, current_url)
            
            try:
                # Get page content
                html_content, content_type = self.get_page_content(current_url)
                if not html_content:
                    continue
                
                # Check if this is a PDF accessed directly
                if content_type and 'pdf' in content_type.lower():
                    found, matched_text = self.check_pdf_content(current_url)
                    if found:
                        self.record_finding(current_url, 'PDF', matched_text, notes='PDF document (direct access)')
                    continue
                
                # Parse HTML content with safe parsing
                soup = self.safe_parse_html(html_content)
                if not soup:
                    print(f"Could not parse HTML for {current_url}")
                    continue
                
                page_text = soup.get_text()
                
                # Check if page contains any target address patterns
                found, matched_text = self.check_address_in_text(page_text)
                if found:
                    title = soup.title.string if soup.title else 'No title'
                    self.record_finding(current_url, 'HTML Page', matched_text, title=title, notes='HTML page content')
                
                # Extract and queue new links
                links = self.extract_links(html_content, current_url)
                for link in links:
                    if (self.is_valid_url(link) and 
                        not self.should_skip_url(link) and  # Skip asset files
                        link not in self.visited_urls and 
                        link not in url_queue):
                        
                        # Check if it's a PDF link
                        if link.lower().endswith('.pdf'):
                            found, matched_text = self.check_pdf_content(link)
                            if found:
                                self.record_finding(link, 'PDF', matched_text, 
                                                  notes='PDF document (linked)', 
                                                  parent_page=current_url)
                        else:
                            url_queue.append(link)
                
            except Exception as e:
                print(f"Error processing {current_url}: {e}")
                continue
            
            # Rate limiting - reduced for faster crawling
            time.sleep(0.2)
        
        print(f"\nCrawl completed. Visited {pages_crawled} pages.")
        self.save_progress(pages_crawled, "COMPLETED")

    def print_summary(self):
        """Print a summary of findings"""
        print(f"\n{'='*60}")
        print(f"CRAWL SUMMARY")
        print(f"{'='*60}")
        print(f"Search patterns used:")
        for i, pattern in enumerate(self.address_patterns, 1):
            print(f"  {i}. {pattern}")
        print(f"Total pages crawled: {len(self.visited_urls)}")
        print(f"HTML pages with address: {len(self.found_pages)}")
        print(f"PDFs with address: {len(self.found_pdfs)}")
        print(f"Results saved to: {self.output_file}")
        
        if self.found_pages:
            print(f"\nHTML Pages containing address patterns:")
            for i, page in enumerate(self.found_pages, 1):
                print(f"{i}. {page['URL']}")
                print(f"   Found: '{page['Address Found']}'")
                if page.get('Title'):
                    print(f"   Title: {page['Title']}")
        
        if self.found_pdfs:
            print(f"\nPDFs containing address patterns:")
            for i, pdf in enumerate(self.found_pdfs, 1):
                print(f"{i}. {pdf['URL']}")
                print(f"   Found: '{pdf['Address Found']}'")
                if pdf.get('Parent Page'):
                    print(f"   Linked from: {pdf['Parent Page']}")


def main():
    """Main function to run the crawler"""
    crawler = SLUSDCrawler()
    
    try:
        # Start crawling
        crawler.crawl_site(max_pages=20000)
        
        # Print summary
        crawler.print_summary()
        
    except KeyboardInterrupt:
        print("\nCrawl interrupted by user.")
        crawler.print_summary()
    except Exception as e:
        print(f"An error occurred: {e}")
        crawler.print_summary()


if __name__ == "__main__":
    # Install required packages if not already installed
    try:
        import PyPDF2
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("Missing required packages. Install them with:")
        print("pip install requests beautifulsoup4 PyPDF2")
        exit(1)
    
    main()