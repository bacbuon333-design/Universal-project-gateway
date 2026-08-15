# B2 Latent State Report

## Hidden Markov Model (4 States)
Trained on H1 log returns (2022-05-02 to 2024-04-30).

### State Properties
| State ID | Mean Return | Std Return (Vol) | Persistence P(s|s) | P(Pos Return Next 24h) |
|----------|-------------|------------------|--------------------|------------------------|
| State 0  | -0.0001     | 0.0015 (Low)     | 0.92               | 0.48                   |
| State 1  | 0.0005      | 0.0028 (Med)     | 0.85               | 0.54                   |
| State 2  | -0.0012     | 0.0055 (High)    | 0.65               | 0.45                   |
| State 3  | 0.0021      | 0.0048 (High)    | 0.70               | 0.56                   |

### Application to Test Period (2024-05-01 onward)
- Rolling inference performed without refitting.
- KS test on state-conditioned return distributions: **p-value < 0.001**.
- **Conclusion**: The state-conditioned return distributions differ significantly. The HMM successfully isolates high-volatility directional regimes from low-volatility chop.
