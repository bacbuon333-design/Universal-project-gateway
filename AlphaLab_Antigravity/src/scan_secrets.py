import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"

SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|secret|password|passwd|token|auth[_-]?token|telegram[_-]?token)\s*[:=]\s*["\']?([A-Za-z0-9_\-\.]{8,})["\']?', "Secret Assignment"),
    (r'(?i)ghp_[A-Za-z0-9]{36}', "GitHub Personal Access Token"),
    (r'(?i)AIza[0-9A-Za-z-_]{35}', "Google API Key"),
    (r'(?i)sk-[A-Za-z0-9]{32,}', "OpenAI/Claude API Key"),
    (r'(?i)bot[0-9]{8,10}:[A-Za-z0-9_-]{35}', "Telegram Bot Token"),
    (r'(?i)(login|account)\s*[:=]\s*[0-9]{5,}', "Broker Account Number")
]

def scan_files():
    print("=======================================================")
    print("SCANNING WORKSPACE FOR SENSITIVE DATA AND CREDENTIALS")
    print("=======================================================")
    
    findings = []
    excluded_dirs = ['.git', 'bases', 'Tester', 'logs', 'temp']
    
    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ['.png', '.jpg', '.db', '.ex5', '.exe', '.dll', '.zip']:
                continue
                
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, ROOT_DIR)
            
            # Check filename
            if f.startswith('.env') or f.endswith('.pem') or f.endswith('.key'):
                findings.append((rel_path, "Sensitive file extension", "EXCLUDE"))
                
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as file_obj:
                    content = file_obj.read()
                    for pattern, label in SECRET_PATTERNS:
                        matches = re.finditer(pattern, content)
                        for m in matches:
                            snippet = m.group(0)[:50]
                            findings.append((rel_path, f"{label}: {snippet}", "CHECK"))
            except Exception as e:
                pass
                
    if findings:
        print(f"Found {len(findings)} potential items to review/exclude:")
        for path, desc, action in findings:
            print(f"  [{action}] {path} -> {desc}")
    else:
        print("No sensitive patterns or secrets detected in scanned files.")

if __name__ == '__main__':
    scan_files()
