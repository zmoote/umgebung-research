import xml.etree.ElementTree as ET
import time
import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Define the sitemaps for all three of your target domains
sitemap_targets = [
    "https://www.elenadanaan.org/sitemap.xml",
    "https://www.elenadanaan.info/sitemap.xml",
    "https://www.elenadanaanindex.org/sitemap.xml"
]

def get_corpus_urls(sitemap_url):
    print(f"Fetching sitemap: {sitemap_url}")
    headers = {"User-Agent": "UmgebungResearchBot/1.0 (Academic/Personal Research)"}
    urls = []
    
    try:
        response = requests.get(sitemap_url, headers=headers, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Check if this is a Sitemap Index (contains nested <sitemap> tags)
            sub_sitemaps = root.findall('.//ns:sitemap/ns:loc', ns)
            if sub_sitemaps:
                print(f"  -> Found sitemap index. Recursively fetching {len(sub_sitemaps)} sub-sitemaps...")
                for loc in sub_sitemaps:
                    sub_url = loc.text
                    urls.extend(get_corpus_urls(sub_url))
            else:
                # This is a standard page sitemap containing <url> tags
                locs = root.findall('.//ns:loc', ns)
                for loc in locs:
                    url = loc.text
                    # Enforce robots.txt rules (no lightboxes or partials)
                    if '?lightbox=' not in url and '_partials' not in url:
                        urls.append(url)
        else:
            print(f"  -> Failed to fetch sitemap. Status: {response.status_code}")
    except Exception as e:
        print(f"  -> Error parsing sitemap {sitemap_url}: {e}")
        
    return urls

def build_master_corpus():
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    output_filepath = data_dir / "umgebung_master_corpus.json"
    
    master_corpus = []
    headers = {"User-Agent": "UmgebungResearchBot/1.0 (Academic/Personal Research)"}
    
    # 1. Collect all valid page URLs across all domains recursively
    all_urls = []
    for sitemap in sitemap_targets:
        domain_urls = get_corpus_urls(sitemap)
        print(f"Found {len(domain_urls)} valid page links in {sitemap}\n")
        all_urls.extend(domain_urls)
        
    # Remove any potential duplicate URLs across sub-sitemaps
    all_urls = list(set(all_urls))
    
    print(f"Total unique research targets collected: {len(all_urls)}\n")
    print("Starting content extraction...")
    
    # 2. Scrape each actual page content
    for index, url in enumerate(all_urls):
        print(f"[{index + 1}/{len(all_urls)}] Processing: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Strip layout clutter
                for noise in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    noise.decompose()
                    
                title = soup.title.string.strip() if soup.title else "Untitled Page"
                
                text_blocks = [
                    p.get_text(strip=True) 
                    for p in soup.find_all(['p', 'article', 'section', 'div']) 
                    if len(p.get_text(strip=True)) > 50
                ]
                
                unique_blocks = []
                for block in text_blocks:
                    if block not in unique_blocks:
                        unique_blocks.append(block)
                
                master_corpus.append({
                    "domain": url.split('/')[2],
                    "url": url,
                    "title": title,
                    "content": "\n\n".join(unique_blocks)
                })
            else:
                print(f"  -> Skipped: HTTP Status {response.status_code}")
                
        except requests.RequestException as e:
            print(f"  -> Network error: {e}")
            
        time.sleep(2)
        
    # 3. Save to the relative data folder path
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(master_corpus, f, ensure_ascii=False, indent=4)
        
    print(f"\n[COMPLETE] Successfully compiled {len(master_corpus)} documents into {output_filepath}")

if __name__ == "__main__":
    build_master_corpus()