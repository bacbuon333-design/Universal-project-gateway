import os, sys

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

SEARCH_PATHS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes",
    r"C:\Users\gugul\Downloads",
    r"C:\Users\gugul\Desktop",
    r"C:\Users\gugul\Documents"
]

def find_html_1317():
    print("="*105)
    print("SEARCHING FOR HTML REPORT FILES CONTAINING '1317'")
    print("="*105)
    
    found_files = []
    
    for search_root in SEARCH_PATHS:
        if not os.path.exists(search_root):
            continue
        for root, dirs, files in os.walk(search_root):
            for file in files:
                if '1317' in file and file.endswith(('.html', '.htm', '.xml', '.txt', '.log')):
                    full_path = os.path.join(root, file)
                    found_files.append(full_path)
                    print(f"FOUND MATCH: {full_path}")
                    
    if not found_files:
        print("No file named *1317* found directly. Searching for ALL html report files in MetaQuotes / Downloads...")
        for search_root in SEARCH_PATHS:
            if not os.path.exists(search_root):
                continue
            for root, dirs, files in os.walk(search_root):
                for file in files:
                    if file.endswith(('.html', '.htm')):
                        full_path = os.path.join(root, file)
                        print(f"FOUND HTML: {full_path}")
                        found_files.append(full_path)

if __name__ == '__main__':
    find_html_1317()
