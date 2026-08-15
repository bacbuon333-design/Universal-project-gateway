"""
EXHAUSTIVE METATRADER 5 OFFICIAL REPORT PARSER & ANALYZER
=========================================================
User Mandate:
"ý minh là ban bắt buoocj phai hoc đc cach sưe dung backtest chay thât backtest mt5. xong r khi backtest xong ban phai lây đc bao caod và phân tich"

Parses official MetaTrader 5 Strategy Tester HTML reports (.html / .htm) and performs comprehensive quantitative analysis.
"""

import os, sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def analyze_mt5_html(html_path):
    print("="*105)
    print(f"OFFICIAL METATRADER 5 STRATEGY TESTER REPORT ANALYSIS: {os.path.basename(html_path)}")
    print("="*105)
    
    if not os.path.exists(html_path):
        print(f"File not found: {html_path}")
        return
        
    try:
        with open(html_path, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        if not content or len(content) < 100 or 'Strategy Tester Report' not in content:
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
    except Exception as e:
        print("Read error:", e)
        return
        
    soup = BeautifulSoup(content, 'html.parser')
    text_content = soup.get_text(separator='\n')
    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
    
    report_data = {}
    
    for i, line in enumerate(lines):
        if line == "Expert:": report_data['Expert'] = lines[i+1]
        elif line == "Symbol:": report_data['Symbol'] = lines[i+1]
        elif line == "Period:": report_data['Period'] = lines[i+1]
        elif line == "Company:": report_data['Company'] = lines[i+1]
        elif line == "Initial Deposit:": report_data['Initial Deposit'] = lines[i+1]
        elif line == "Total Net Profit:": report_data['Total Net Profit'] = lines[i+1]
        elif line == "Gross Profit:": report_data['Gross Profit'] = lines[i+1]
        elif line == "Gross Loss:": report_data['Gross Loss'] = lines[i+1]
        elif line == "Profit Factor:": report_data['Profit Factor'] = lines[i+1]
        elif line == "Sharpe Ratio:": report_data['Sharpe Ratio'] = lines[i+1]
        elif line == "Recovery Factor:": report_data['Recovery Factor'] = lines[i+1]
        elif line == "Balance Drawdown Maximal:": report_data['Balance Drawdown Maximal'] = lines[i+1]
        elif line == "Equity Drawdown Maximal:": report_data['Equity Drawdown Maximal'] = lines[i+1]
        elif line == "Total Trades:": report_data['Total Trades'] = lines[i+1]
        elif line == "Profit Trades (% of total):": report_data['Profit Trades'] = lines[i+1]
        elif line == "Loss Trades (% of total):": report_data['Loss Trades'] = lines[i+1]
        elif line == "Average profit trade:": report_data['Average Profit Trade'] = lines[i+1]
        elif line == "Average loss trade:": report_data['Average Loss Trade'] = lines[i+1]
        elif line == "Largest profit trade:": report_data['Largest Profit Trade'] = lines[i+1]
        elif line == "Largest loss trade:": report_data['Largest Loss Trade'] = lines[i+1]
        elif line == "Maximum consecutive wins ($):": report_data['Max Consecutive Wins'] = lines[i+1]
        elif line == "Maximum consecutive losses ($):": report_data['Max Consecutive Losses'] = lines[i+1]
        
    print(f"1. Tên Chiến Lược / Robot EA : {report_data.get('Expert', 'N/A')}")
    print(f"2. Sản Phẩm & Khung Thời Gian: {report_data.get('Symbol', 'N/A')} ({report_data.get('Period', 'N/A')})")
    print(f"3. Máy Chủ / Sàn Giao Dịch  : {report_data.get('Company', 'N/A')}")
    print(f"4. Vốn Ban Đầu (Deposit)     : ${report_data.get('Initial Deposit', 'N/A')} USD")
    print(f"5. LỢI NHUẬN RÒNG (NET PROFIT): +${report_data.get('Total Net Profit', 'N/A')} USD")
    print(f"6. Tổng Lời / Tổng Lỗ       : +${report_data.get('Gross Profit', 'N/A')} USD / ${report_data.get('Gross Loss', 'N/A')} USD")
    print(f"7. Hệ Số Profit Factor (PF)   : {report_data.get('Profit Factor', 'N/A')}")
    print(f"8. Chỉ Số Risk-Adjust (Sharpe): {report_data.get('Sharpe Ratio', 'N/A')}")
    print(f"9. Hệ Số Phục Hồi (Recovery) : {report_data.get('Recovery Factor', 'N/A')}")
    print(f"10. Sụt Giảm Tối Đa (MaxDD)   : {report_data.get('Balance Drawdown Maximal', 'N/A')} (Balance) / {report_data.get('Equity Drawdown Maximal', 'N/A')} (Equity)")
    print(f"11. Tổng Số Lệnh Đánh        : {report_data.get('Total Trades', 'N/A')} Lệnh")
    print(f"12. Số Lệnh Thắng (Win Rate)  : {report_data.get('Profit Trades', 'N/A')}")
    print(f"13. Số Lệnh Thua (Loss Rate)  : {report_data.get('Loss Trades', 'N/A')}")
    print(f"14. Thắng Trung Bình / Lỗ TB : +${report_data.get('Average Profit Trade', 'N/A')} USD / ${report_data.get('Average Loss Trade', 'N/A')} USD")
    print(f"15. Thắng Lớn Nhất / Lỗ LN   : +${report_data.get('Largest Profit Trade', 'N/A')} USD / ${report_data.get('Largest Loss Trade', 'N/A')} USD")
    print(f"16. Chuỗi Thắng / Chuỗi Lỗ   : {report_data.get('Max Consecutive Wins', 'N/A')} / {report_data.get('Max Consecutive Losses', 'N/A')}")
    print("="*105)

if __name__ == '__main__':
    html_1317 = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\1317.html"
    analyze_mt5_html(html_1317)
