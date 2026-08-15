import os, sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

HTML_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\1317.html"

def parse_1317_html():
    if not os.path.exists(HTML_PATH):
        print(f"File not found: {HTML_PATH}")
        return
        
    with open(HTML_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
        content = f.read()
        
    if not content or len(content) < 100:
        with open(HTML_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
    soup = BeautifulSoup(content, 'html.parser')
    
    print("="*105)
    print("PARSE REPORT FROM MT5 STRATEGY TESTER FILE: 1317.html")
    print("="*105)
    
    title = soup.find('title')
    if title:
        print("Report Title:", title.get_text(strip=True))
        
    tables = soup.find_all('table')
    print(f"Total HTML Tables found: {len(tables)}")
    
    text_content = soup.get_text(separator='\n')
    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
    
    print("\n--- KEY REPORT SUMMARY EXTRACTED FROM HTML ---")
    for i, line in enumerate(lines[:100]):
        print(f"{i+1:02d}: {line}")
        
    print("="*105)

if __name__ == '__main__':
    parse_1317_html()
