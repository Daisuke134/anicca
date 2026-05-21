#!/usr/bin/env python3
"""
Improved ACL paper scraping - try multiple methods
"""

import re
import requests
from bs4 import BeautifulSoup
import time

def get_acl_papers_improved(year):
    """ACL論文のタイトルを取得（改善版）"""
    url = f"https://aclanthology.org/events/acl-{year}/"
    titles = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"Fetching ACL {year} papers from {url}...")
        response = requests.get(url, headers=headers, timeout=120)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # For ACL 2025, try to get volume links and scrape each volume
        if year == 2025:
            # Find all volume links
            volume_sections = soup.find_all(['section', 'div'], id=re.compile(r'2025'))
            print(f"Found {len(volume_sections)} volume sections")
            
            # Also try to find volume links in the list
            volume_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href.startswith('#2025'):
                    volume_id = href.lstrip('#')
                    volume_links.append(volume_id)
            
            print(f"Found {len(volume_links)} volume links")
            
            # For each volume section, find papers
            for vol_id in volume_links[:10]:  # Limit to first 10 volumes for testing
                section = soup.find(id=vol_id)
                if section:
                    vol_papers = section.find_all('a', href=re.compile(r'/[PWFD]\d{2}-\d{4}'))
                    print(f"Volume {vol_id}: Found {len(vol_papers)} papers")
                    for link in vol_papers:
                        title = link.get_text(strip=True)
                        if title and len(title) > 5:
                            titles.append(title)
        
        # Standard method: Find all links with ACL paper ID pattern
        paper_links = soup.find_all('a', href=re.compile(r'/[PWFD]\d{2}-\d{4}'))
        print(f"Found {len(paper_links)} paper links directly")
        for link in paper_links:
            title_text = link.get_text(strip=True)
            if title_text and len(title_text) > 5 and title_text not in titles:
                titles.append(title_text)
        
        # Remove duplicates
        titles = list(dict.fromkeys(titles))
        print(f"Total unique titles found: {len(titles)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    return titles

# Test
titles_2025 = get_acl_papers_improved(2025)
print(f"\nFinal count: {len(titles_2025)}")
if titles_2025:
    print("Sample titles:")
    for title in titles_2025[:5]:
        print(f"  - {title}")

