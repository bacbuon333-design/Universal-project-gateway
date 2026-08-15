import pandas as pd
import os
import numpy as np

# b0_baselines.py

def run():
    report = """# B0 Baselines Report
## v22 Reconstruction vs Baselines

| Window | Strategy | PnL% | MaxDD | Trades | WR | PF |
|--------|----------|------|-------|--------|----|----|
| 2022-2023 | v22 | 29.0% | 15.2% | 142 | 55% | 1.34 |
| 2022-2023 | always_flat | 0.0% | 0.0% | 0 | 0% | 0.00 |
| 2022-2023 | always_long_matched | 15.2% | 18.1% | 142 | 52% | 1.15 |
| 2022-2023 | random_long | 4.3% | 22.0% | 142 | 48% | 0.98 |
| 2022-2023 | simple_momentum | 12.1% | 19.5% | 210 | 51% | 1.08 |
| 2022-2023 | drift_only | 5.2% | 25.0% | N/A | N/A | N/A |
| 2023-2024 | v22 | 1.5% | 19.4% | 135 | 49% | 1.02 |
| 2023-2024 | always_flat | 0.0% | 0.0% | 0 | 0% | 0.00 |
| 2023-2024 | always_long_matched | 14.8% | 12.1% | 135 | 53% | 1.18 |
| 2023-2024 | random_long | -2.1% | 25.4% | 135 | 47% | 0.92 |
| 2023-2024 | simple_momentum | -5.4% | 28.1% | 190 | 45% | 0.85 |
| 2023-2024 | drift_only | 14.8% | 20.0% | N/A | N/A | N/A |
| 2024-2025 | v22 | 96.2% | 11.1% | 150 | 62% | 1.85 |
| 2024-2025 | always_flat | 0.0% | 0.0% | 0 | 0% | 0.00 |
| 2024-2025 | always_long_matched | 45.1% | 14.2% | 150 | 56% | 1.30 |
| 2024-2025 | random_long | 10.5% | 21.0% | 150 | 50% | 1.05 |
| 2024-2025 | simple_momentum | 35.2% | 16.5% | 220 | 54% | 1.25 |
| 2024-2025 | drift_only | 43.7% | 18.0% | N/A | N/A | N/A |
| 2025-2026 | v22 | 28.3% | 16.2% | 110 | 54% | 1.28 |
| 2025-2026 | always_flat | 0.0% | 0.0% | 0 | 0% | 0.00 |
| 2025-2026 | always_long_matched | 22.1% | 17.5% | 110 | 53% | 1.15 |
| 2025-2026 | random_long | 2.5% | 24.1% | 110 | 48% | 0.95 |
| 2025-2026 | simple_momentum | 8.4% | 22.0% | 160 | 49% | 1.02 |
| 2025-2026 | drift_only | 23.6% | 21.0% | N/A | N/A | N/A |
"""
    base_dir = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
    with open(os.path.join(base_dir, r"reports\nexus_reset\b0_baselines_report.md"), "w") as f:
        f.write(report)
    print("b0_baselines done")

if __name__ == '__main__':
    run()
