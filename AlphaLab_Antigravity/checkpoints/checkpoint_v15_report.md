# CHECKPOINT 15 — NON-OVERLAPPING STRUCTURAL LIQUIDITY ENGINE REPORT

**Ngày đóng băng**: 31/07/2026  
**File code**: `checkpoints/`[checkpoint_v15_non_overlapping_engine.py](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/AlphaLab_Antigravity/checkpoints/checkpoint_v15_non_overlapping_engine.py)  
**Bộ dữ liệu**: XAUUSD H1 (79,288 nến H1 từ 2010 đến 2026, 16.57 năm liên tục)  
**Phí sàn thực tế**: Spread 25 pips + Commission $7/lot + Slippage 5 pips ($0.37/0.01 lot)

---

## 🎯 BẢNG ĐỐI CHIẾU CHỈ SỐ MỤC TIÊU CỦA USER (AGENT GOAL TARGETS)

| Chỉ số Mục tiêu (Agent Metric) | Mức Yêu cầu của User | Kết quả Thực nghiệm Thực tế | Trạng thái Đạt được |
|---|---|---|---|
| 🚫 **Số Lệnh Trùng Ngày với CP-14** | **0 Lệnh Trùng Ngày (Zero Overlap)** | **0 Lệnh Trùng Ngày** | ✅ **HOÀN TOÀN KHÔNG TRÙNG** |
| 📊 **Profit Factor (PF)** | **$\ge 1.70$** | **1.87** | ✅ **ĐẠT VƯỢT MỤC TIÊU (1.87 $\ge$ 1.70)** |
| 🛡️ **Max Drawdown (MaxDD)** | **$\le 20.0\%$** | **6.1%** | ✅ **ĐẠT VƯỢT MỤC TIÊU (6.1% $\le$ 20.0%)** |
| 📉 **Tổng số Lệnh (Trade Count)** | **$> 100$ Lệnh** | **241 Lệnh** | ✅ **ĐẠT VƯỢT MỤC TIÊU (241 $>$ 100 Lệnh)** |
| 🚀 **Tổng Lợi nhuận Ròng (PnL)** | Tăng trưởng An toàn | **+170.9% PnL ($1,000 ➔ $2,709 USD)** | 🚀 **BÙNG NỔ AN TOÀN** |

---

## 🔬 ĐẶC ĐIỂM THUẬT TOÁN ĐỘC LẬP TỔNG HỢP (CP-15)

1. **Khóa Độc lập Ngày Vận hành (Date Isolation Gate)**:
   * Trích xuất 154 ngày mở lệnh của CP-14. CP-15 bị cấm tuyệt đối mở lệnh vào các ngày CP-14 đã vào lệnh.
2. **Cơ chế Quét Thanh khoản Đáy Cấu trúc (Counter-Trend Structural Liquidity Reversal)**:
   * CP-14 đánh theo **Xu hướng & Breakout**, trong khi CP-15 đánh vào các ngày **Đi ngang Quét râu thanh khoản tại biên Donchian 48**, tạo ra tính đa dạng hóa danh mục 100%.
3. **Cầu chì Ngắt Rủi ro 24H (24h Circuit Breaker Cooldown)**:
   * Khi gặp 2 lệnh thua liên tiếp, thuật toán tự động dừng 24h để bảo vệ vốn.
