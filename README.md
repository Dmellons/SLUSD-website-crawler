# SLUSD Website Crawler

A Python web crawler designed to audit the San Leandro Unified School District (SLUSD) website for specific address references that may need updating. The crawler searches through HTML pages and PDF documents to identify content containing target addresses.

## Overview

This project was created to help identify all instances of specific addresses across the SLUSD website (`www.slusd.us`), making it easier to update address information systematically. The crawler supports multiple address pattern matching and provides detailed reporting of findings.

## Features

- **Comprehensive Web Crawling**: Crawls HTML pages and PDF documents
- **Multiple Address Pattern Matching**: Uses regex patterns to catch various address formats
- **Real-time Progress Tracking**: Saves progress and results continuously during crawling
- **Performance Optimized**: Includes URL filtering and quick pre-checks to improve speed
- **CSV Export**: Results are saved in CSV format for easy analysis
- **Robust Error Handling**: Handles network issues, parsing errors, and malformed content gracefully

## Target Addresses

The crawler is configured to search for two main addresses:

### 835 E. 14th Street
Patterns detected:
- `835 E. 14th St` (various punctuation)
- `835 East 14th Street`
- `835 14th St`
- `835 E 14` (abbreviated forms)

### 14735 Juniper Street
Patterns detected:
- `14735 Juniper St` (various punctuation)
- `14735 Juniper Street`
- `14735 North Juniper St`
- `14735 N Juniper` (abbreviated forms)

## Files in Repository

### Core Crawler Scripts
- **`web_crawler.py`** - Basic crawler implementation
- **`web_crawler_regex.py`** - Enhanced version with regex pattern matching
- **`web_crawler_regex_fast.py`** - Optimized version for faster crawling (835 E. 14th St)
- **`web_crawler_regex_fast_juniper.py`** - Optimized version for Juniper Street address

### Progress and Output Files
- **`crawl_progress.txt`** - Progress tracking for 835 E. 14th St crawl
- **`crawl_progress_juniper.txt`** - Progress tracking for Juniper St crawl
- **`.gitignore`** - Git ignore rules (excludes CSV outputs, logs, environment files)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd slusd-website-crawler
   ```

2. **Install required Python packages**:
   ```bash
   pip install requests beautifulsoup4 PyPDF2 lxml html5lib
   ```

## Usage

### Basic Usage

Run the crawler for 835 E. 14th Street:
```bash
python web_crawler_regex_fast.py
```

Run the crawler for 14735 Juniper Street:
```bash
python web_crawler_regex_fast_juniper.py
```

### Advanced Options

You can modify the crawling parameters by editing the script:

```python
# In the main() function or SLUSDCrawler class
crawler.crawl_site(max_pages=20000)  # Adjust max pages to crawl
```

## Output Files

### CSV Results
- **`slusd_address_audit.csv`** - Results for 835 E. 14th St search
- **`slusd_juniper_audit.csv`** - Results for Juniper St search

CSV columns:
- `URL` - The webpage or PDF URL where address was found
- `Type` - Content type (HTML Page or PDF)
- `Title` - Page title (for HTML pages)
- `Address Found` - The exact address text that matched
- `Notes` - Additional context about the finding
- `Parent Page` - The page that linked to this content (for PDFs)
- `Timestamp` - When the finding was recorded

### Progress Files
- **`crawl_progress.txt`** - Real-time crawling statistics
- **`crawl_progress_juniper.txt`** - Progress for Juniper Street crawl

## Recent Crawl Results

Based on the progress files in the repository:

### 835 E. 14th Street Crawl
- **Pages crawled**: 20,000
- **Status**: COMPLETED
- **HTML pages found**: 3,343
- **PDFs found**: 2,918
- **Last update**: June 24, 2025

### 14735 Juniper Street Crawl
- **Pages crawled**: 20,000  
- **Status**: COMPLETED
- **HTML pages found**: 2
- **PDFs found**: 1,305
- **Last update**: June 24, 2025

## Technical Details

### Performance Optimizations
- **URL Filtering**: Skips asset files (CSS, JS, images) to focus on content
- **Quick Pre-checks**: Uses simple string matching before expensive regex operations
- **Rate Limiting**: Includes delays to be respectful to the target server
- **File Size Limits**: Skips large PDF files to avoid excessive download times

### Error Handling
- Multiple HTML parser fallbacks (html.parser, lxml, html5lib)
- Network timeout handling
- Malformed content recovery
- Progress persistence across interruptions

### Pattern Matching
Uses compiled regex patterns for efficient matching of various address formats including:
- Different punctuation styles
- Abbreviated vs. full street names
- Various spacing patterns
- Directional prefixes (E., East, N., North)

## Configuration

### Modifying Search Patterns
To add new address patterns, edit the `address_patterns` list in the crawler class:

```python
self.address_patterns = [
    r'your_new_pattern_here',
    # existing patterns...
]
```

### Adjusting Crawl Scope
- Modify `max_pages` parameter to control crawl depth
- Update `base_url` to target different domains
- Adjust `time.sleep()` values for different rate limiting

## Notes

- The crawler respects robots.txt and includes rate limiting
- Results are saved continuously to prevent data loss
- Large PDF files (>50MB for Juniper crawler, >100MB for others) are automatically skipped
- All crawling is limited to the slusd.us domain and subdomains

