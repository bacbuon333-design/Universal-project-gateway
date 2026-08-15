//+------------------------------------------------------------------+
//|                        ALAB LiveBot v1.mq5                     |
//|         Causal Market Intelligence Engine — DEMO ONLY          |
//|  Architecture: HMM State × Corrected Signals × Dynamic Risk   |
//|  Status: SHADOW / DEMO — NOT ARMED FOR LIVE TRADING            |
//+------------------------------------------------------------------+
#property copyright "AlphaLab Antigravity Research"
#property version   "1.00"
#property strict

//─── INPUT PARAMETERS ────────────────────────────────────────────────────────
input double RiskPct        = 0.055;  // Risk per trade (fraction of equity)
input int    CooldownBars   = 96;     // Min bars between trades (H1)
input double ATR_Period     = 14;     // ATR lookback
input double MinScore       = 4;      // Min conviction score for pullback signal
input bool   AllowShort     = true;   // Enable SHORT signals (macro-bear regime)
input bool   DemoOnly       = true;   // Safety: refuse to open live trades

//─── HMM PARAMETERS (from Python fit) ────────────────────────────────────────
double HMM_Mus[4]  = { -0.000056, -0.000043, 0.000087, 0.000421 };
double HMM_Sigs[4] = { 0.001776, 0.000641, 0.000931, 0.004768 };

//─── GLOBAL STATE ────────────────────────────────────────────────────────────
datetime g_LastTradeTime = 0;
int      g_CurrentHMMState = -1;
double   g_ATR = 0;

//─── UTILITY FUNCTIONS ───────────────────────────────────────────────────────
double CalcATR(int period, int shift = 0)
{
    double atr = 0;
    for(int i = 0; i < period; i++)
    {
        double hi = iHigh(_Symbol, PERIOD_H1, shift+i);
        double lo = iLow(_Symbol,  PERIOD_H1, shift+i);
        double pc = iClose(_Symbol, PERIOD_H1, shift+i+1);
        double tr = MathMax(hi-lo, MathMax(MathAbs(hi-pc), MathAbs(lo-pc)));
        atr += tr;
    }
    return atr / period;
}

double CalcEMA(int period, int shift = 0)
{
    // Use built-in iMA for reliability
    return iMA(_Symbol, PERIOD_H1, period, 0, MODE_EMA, PRICE_CLOSE, shift);
}

double CalcRSI(int period, int shift = 0)
{
    return iRSI(_Symbol, PERIOD_H1, period, PRICE_CLOSE, shift);
}

bool MacroBull3Month()
{
    double cur  = iClose(_Symbol, PERIOD_H1, 1);
    double past = iClose(_Symbol, PERIOD_H1, 1441);  // ~3 months ago
    double ema200 = CalcEMA(200, 1);
    return (cur > past) && (cur > ema200);
}

bool MacroBear3Month()
{
    double cur  = iClose(_Symbol, PERIOD_H1, 1);
    double past = iClose(_Symbol, PERIOD_H1, 1441);
    double ema200 = CalcEMA(200, 1);
    return (cur < past) && (cur < ema200);
}

int EstimateHMMState(int lookback = 60)
{
    // Simple Gaussian HMM state estimation via max-likelihood emission
    double lr_sum = 0;
    int n = MathMin(lookback, Bars(_Symbol, PERIOD_H1) - 2);
    for(int i = 1; i <= n; i++)
    {
        double c1 = iClose(_Symbol, PERIOD_H1, i+1);
        double c0 = iClose(_Symbol, PERIOD_H1, i);
        if(c1 > 0) lr_sum += MathLog(c0 / c1);
    }
    double lr_mean = lr_sum / n;

    int best_state = 0;
    double best_prob = -1e9;
    for(int s = 0; s < 4; s++)
    {
        double diff = lr_mean - HMM_Mus[s];
        double sig2 = HMM_Sigs[s] * HMM_Sigs[s];
        double prob = -0.5 * (diff*diff / (sig2+1e-12)) - MathLog(HMM_Sigs[s]+1e-12);
        if(prob > best_prob) { best_prob = prob; best_state = s; }
    }
    return best_state;
}

double CalcDonchianHigh(int period, int shift = 1)
{
    double hi = -1e9;
    for(int i = shift; i < shift+period; i++)
        hi = MathMax(hi, iHigh(_Symbol, PERIOD_H1, i));
    return hi;
}

double CalcDonchianLow(int period, int shift = 1)
{
    double lo = 1e9;
    for(int i = shift; i < shift+period; i++)
        lo = MathMin(lo, iLow(_Symbol, PERIOD_H1, i));
    return lo;
}

double CalcVariableSpread()
{
    double sp_pts = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
    return MathMax(sp_pts, 25.0 * _Point);  // Min 25 pip spread
}

double CalcLotSize(double sl_points)
{
    double equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double peak   = MathMax(equity, AccountInfoDouble(ACCOUNT_BALANCE));
    double dd_pct = (peak - equity) / (peak + 1e-9) * 100.0;
    double r_scale = 1.0;
    if(dd_pct >= 15.0) r_scale = 0.15;
    else if(dd_pct >= 10.0) r_scale = 0.40;

    double risk_amount = equity * RiskPct * r_scale;
    double tick_value  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double tick_size   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
    if(tick_value <= 0 || tick_size <= 0) return 0.01;

    double lot = risk_amount / (sl_points / tick_size * tick_value);
    double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    double max_lot = MathMin(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX), 25.0);
    double step    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
    lot = MathMax(min_lot, MathMin(max_lot, MathFloor(lot/step)*step));
    return lot;
}

bool CooldownActive()
{
    int h1_bars_since = (int)((TimeCurrent() - g_LastTradeTime) / 3600);
    return h1_bars_since < CooldownBars;
}

void OpenTrade(int direction, double sl_pts, double rr, string comment)
{
    if(DemoOnly && AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
    {
        Print("⛔ LIVE ACCOUNT DETECTED — DemoOnly=true — Trade blocked!");
        return;
    }

    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double lot = CalcLotSize(sl_pts);
    double sl, tp, ep;

    if(direction == 1)  // LONG
    {
        ep = ask;
        sl = ep - sl_pts;
        tp = ep + sl_pts * rr;
        MqlTradeRequest req = {};
        req.action    = TRADE_ACTION_DEAL;
        req.symbol    = _Symbol;
        req.volume    = lot;
        req.type      = ORDER_TYPE_BUY;
        req.price     = ep;
        req.sl        = NormalizeDouble(sl, _Digits);
        req.tp        = NormalizeDouble(tp, _Digits);
        req.comment   = comment + " | HMM=" + IntegerToString(g_CurrentHMMState);
        req.magic     = 202601;
        req.deviation = 20;
        MqlTradeResult res = {};
        OrderSend(req, res);
        if(res.retcode == TRADE_RETCODE_DONE)
        {
            g_LastTradeTime = TimeCurrent();
            Print("✅ BUY opened: lot=", lot, " SL=", sl, " TP=", tp);
        }
        else Print("❌ BUY failed: ", res.retcode, " ", res.comment);
    }
    else  // SHORT
    {
        ep = bid;
        sl = ep + sl_pts;
        tp = ep - sl_pts * rr;
        MqlTradeRequest req = {};
        req.action    = TRADE_ACTION_DEAL;
        req.symbol    = _Symbol;
        req.volume    = lot;
        req.type      = ORDER_TYPE_SELL;
        req.price     = ep;
        req.sl        = NormalizeDouble(sl, _Digits);
        req.tp        = NormalizeDouble(tp, _Digits);
        req.comment   = comment + " | HMM=" + IntegerToString(g_CurrentHMMState);
        req.magic     = 202601;
        req.deviation = 20;
        MqlTradeResult res = {};
        OrderSend(req, res);
        if(res.retcode == TRADE_RETCODE_DONE)
        {
            g_LastTradeTime = TimeCurrent();
            Print("✅ SELL opened: lot=", lot, " SL=", sl, " TP=", tp);
        }
        else Print("❌ SELL failed: ", res.retcode, " ", res.comment);
    }
}

bool HasOpenPosition()
{
    for(int i = PositionsTotal()-1; i >= 0; i--)
        if(PositionGetSymbol(i) == _Symbol && PositionGetInteger(POSITION_MAGIC) == 202601)
            return true;
    return false;
}

//─── OnTick ──────────────────────────────────────────────────────────────────
void OnTick()
{
    // Only run on new H1 bar open
    static datetime lastBar = 0;
    datetime curBar = iTime(_Symbol, PERIOD_H1, 0);
    if(curBar == lastBar) return;
    lastBar = curBar;

    // Skip if position already open
    if(HasOpenPosition()) return;
    if(CooldownActive()) return;

    // Estimate HMM state
    g_CurrentHMMState = EstimateHMMState(60);

    // Build indicators
    g_ATR = CalcATR((int)ATR_Period, 1);
    double rsi     = CalcRSI(14, 1);
    double ema21   = CalcEMA(21, 1);
    double ema50   = CalcEMA(50, 1);
    double ema200  = CalcEMA(200, 1);
    double dc20hi  = CalcDonchianHigh(20, 1);
    double dc20lo  = CalcDonchianLow(20, 1);
    double close1  = iClose(_Symbol, PERIOD_H1, 1);
    double close2  = iClose(_Symbol, PERIOD_H1, 2);
    double spr_pts = CalcVariableSpread();

    bool bull = MacroBull3Month();
    bool bear = MacroBear3Month();

    double sl_d;

    //── LONG: Parabolic Breakout ──────────────────────────────────────────
    if(bull && close1 > dc20hi && close2 <= dc20hi && rsi <= 72)
    {
        sl_d = g_ATR * 1.3 + spr_pts;
        Print("[SIGNAL] LONG Breakout | State=", g_CurrentHMMState, " RSI=", rsi);
        OpenTrade(1, sl_d, 4.0, "BRK_BUY");
        return;
    }

    //── LONG: Pullback to EMA21 ───────────────────────────────────────────
    double low1 = iLow(_Symbol, PERIOD_H1, 1);
    if(bull && low1 <= ema21 && close1 > ema21 && rsi <= 68)
    {
        int sc = 0;
        if(close1 > ema200) sc++;
        if(ema50 > ema200) sc++;
        sc += 2; // at EMA21

        // Bullish pin bar check
        double open1  = iOpen(_Symbol, PERIOD_H1, 1);
        double high1  = iHigh(_Symbol, PERIOD_H1, 1);
        double body   = MathAbs(close1 - open1) + 1e-9;
        double lwick  = MathMin(open1, close1) - low1;
        if(lwick >= 2.0*body && lwick >= 0.5*(high1-low1)) sc += 3;

        if(sc >= (int)MinScore)
        {
            sl_d = g_ATR * 1.4 + spr_pts;
            Print("[SIGNAL] LONG Pullback | Score=", sc, " State=", g_CurrentHMMState);
            OpenTrade(1, sl_d, 3.5, "PB_BUY");
            return;
        }
    }

    //── SHORT: Macro Bear Breakdown ────────────────────────────────────────
    if(AllowShort && bear && close1 < dc20lo && close2 >= dc20lo && rsi >= 30)
    {
        sl_d = g_ATR * 1.35 + spr_pts;
        Print("[SIGNAL] SHORT Breakdown | State=", g_CurrentHMMState, " RSI=", rsi);
        OpenTrade(-1, sl_d, 3.5, "BRK_SELL");
        return;
    }
}

//─── OnInit / OnDeinit ───────────────────────────────────────────────────────
int OnInit()
{
    Print("🤖 ALAB LiveBot v1 initialized");
    Print("   Symbol    : ", _Symbol);
    Print("   Account   : ", AccountInfoInteger(ACCOUNT_LOGIN));
    Print("   Mode      : ", AccountInfoInteger(ACCOUNT_TRADE_MODE) == 0 ? "DEMO" : "LIVE");
    Print("   DemoOnly  : ", DemoOnly ? "TRUE (safe)" : "FALSE (danger!)");
    if(AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO && DemoOnly)
        Print("⚠️  WARNING: Live account but DemoOnly=true — all trades will be blocked");
    return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
    Print("🛑 ALAB LiveBot v1 stopped. Reason: ", reason);
}
//+------------------------------------------------------------------+
