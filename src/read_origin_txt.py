import os, sys

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

ORIGIN_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\origin.txt"

def read_origin():
    if os.path.exists(ORIGIN_PATH):
        with open(ORIGIN_PATH, 'rb') as f:
            raw = f.read()
        print("Raw Origin Bytes:", raw)
        try:
            print("Decoded UTF-16LE:", raw.decode('utf-16-le', errors='ignore'))
        except:
            pass

if __name__ == '__main__':
    read_origin()
