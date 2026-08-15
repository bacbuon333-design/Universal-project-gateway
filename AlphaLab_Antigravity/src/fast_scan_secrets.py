import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"

SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|secret|password|passwd|auth[_-]?token|telegram[_-]?token)\s*[:=]\s*["\']([A-Za-z0-9_\-\.]{8,})["\']', "Secret Assignment"),
    (r'(?i)ghp_[A-Za-z0-9]{36}', "GitHub Token"),
    (r'(?i)AIza[0-9A-Za-z-_]{35}', "Google API Key"),
    (r'(?i)sk-[A-Za-z0-9]{32,}', "OpenAI API Key")
]

def fast_scan():
    print("=======================================================")
    print("FAST TARGETED SECURITY & SECRET AUDIT")
    print("=======================================================")
    
    scan_dirs = ['AlphaLab_Antigravity', 'checkpoints', 'governance']
    findings = []
    
    # 1. Scan root files
    for f in os.listdir(ROOT_DIR):
        p = os.path.join(ROOT_DIR, f)
        if os.path.isfile(p):
            if f.startswith('.env') or f.endswith('.pem') or f.endswith('.key'):
                findings.append((f, "Sensitive file extension", "EXCLUDE"))
            elif f.endswith('.md') or f.endswith('.json') or f.endswith('.py') or f.endswith('.ini'):
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as fo:
                        text = fo.read()
                        for pat, lbl in SECRET_PATTERNS:
                            for m in re.finditer(pat, text):
                                findings.append((f, f"{lbl}: {m.group(0)[:40]}", "FLAG"))
                except:
                    pass
                    
    # 2. Scan targeted directories
    for sdir in scan_dirs:
        dir_path = os.path.join(ROOT_DIR, sdir)
        if not os.path.exists(dir_path):
            continue
        for root, _, files in os.walk(dir_path):
            for f in files:
                if f.endswith('.py') or f.endswith('.json') or f.endswith('.md') or f.endswith('.ini') or f.startswith('.env'):
                    path = os.path.join(root, f)
                    rel = os.path.relpath(path, ROOT_DIR)
                    if f.startswith('.env') or f.endswith('.pem') or f.endswith('.key'):
                        findings.append((rel, "Sensitive file extension", "EXCLUDE"))
                        continue
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as fo:
                            text = fo.read()
                            for pat, lbl in SECRET_PATTERNS:
                                for m in re.finditer(pat, text):
                                    findings.append((rel, f"{lbl}: {m.group(0)[:40]}", "FLAG"))
                    except:
                        pass
                        
    if findings:
        print(f"Found {len(findings)} potential security findings:")
        for rel, desc, act in findings:
            print(f"  [{act}] {rel} -> {desc}")
    else:
        print("✅ CLEAN: No secrets, private keys, or API tokens found in research codebases.")

if __name__ == '__main__':
    fast_scan()
