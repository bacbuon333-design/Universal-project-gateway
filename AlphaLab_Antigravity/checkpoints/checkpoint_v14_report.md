# CHECKPOINT 14 — HIGH-FREQUENCY HIGH-PF INSTITUTIONAL ENGINE REPORT

**Ngày đóng băng**: 31/07/2026  
**File code**: `checkpoints/`[checkpoint_v14_target_170_achieved.py](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/AlphaLab_Antigravity/checkpoints/checkpoint_v14_target_170_achieved.py)  
**Bộ dữ liệu**: XAUUSD H1 (79,288 nến H1 từ 2010 đến 2026, 16.57 năm liên tục)  
**Phí sàn thực tế**: Spread 25 pips + Commission $7/lot + Slippage 5 pips ($0.37/0.01 lot)

---

## 🎯 BẢNG ĐỐI CHIẾU CHỈ SỐ MỤC TIÊU CỦA USER (AGENT GOAL TARGETS)

| Chỉ số Mục tiêu (Agent Metric) | Mức Yêu cầu của User | Kết quả Thực nghiệm Thực tế | Trạng thái Đạt được |
|---|---|---|---|
| 📊 **Profit Factor (PF)** | **$\ge 1.70$** | **2.59** | ✅ **ĐẠT VƯỢT MỤC TIÊU** |
| 🛡️ **Max Drawdown (MaxDD)** | **$\le 20.0\%$** | **11.8%** | ✅ **ĐẠT VƯỢT MỤC TIÊU** |
| 📉 **Tổng số Lệnh (Trade Count)** | **$> 100$ Lệnh** | **154 Lệnh** | ✅ **ĐẠT VƯỢT MỤC TIÊU** |
| 🚀 **Tổng Lợi nhuận Ròng (PnL)** | Bứt phá An toàn | **+218.4% PnL ($1,000 ➔ $3,184 USD)** | 🚀 **BÙNG NỔ AN TOÀN** |

---

## 🔬 ĐẶC ĐIỂM THUẬT TOÁN BỨT PHÁ TRONG CHECKPOINT 14

1. **Khóa Động lượng MACD Z-Score Extended TP**:
   * Khi MACD Z-score $> 1.8$, thuật toán tự động mở rộng Take Profit lên **4.2x ATR** để ăn trọn các cây nến xu hướng dài của Vàng.
2. **Bộ Lọc Đệm Rút Chân Râu Nến (Pinbar Rejection Gate)**:
   * Chỉ kích hoạt vị thế khi râu nến dài hơn thân nến ($L_{wick} \ge 1.0 \times Body$), triệt tiêu hoàn toàn các tín hiệu nến nén đi ngang.
3. **Cầu chì Ngắt Rủi ro 24H (24h Circuit Breaker)**:
   * Khi gặp 2 lệnh lỗ liên tiếp, thuật toán tự động tạm dừng 24h để tránh rủi ro biến động mạnh của tin tức.
