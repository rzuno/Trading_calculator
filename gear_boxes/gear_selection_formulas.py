"""
Gear Selection Formulas for AI Seesaw Trading v2.0
5 candidate models for automated gear selection
"""

import numpy as np
import pandas as pd

# ============================================================================
# UTILITY FUNCTIONS (Calculate Technical Indicators)
# ============================================================================

def calculate_atr(high, low, close, period=5):
    """Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

def calculate_atr_percent(high, low, close, period=5):
    """ATR as percentage of price"""
    atr = calculate_atr(high, low, close, period)
    atr_pct = (atr / close) * 100
    return atr_pct

def calculate_historical_volatility(close, period=10):
    """Historical volatility (annualized std dev of returns)"""
    returns = close.pct_change()
    hv = returns.rolling(period).std() * np.sqrt(252) * 100
    return hv

def calculate_roc(close, period=5):
    """Rate of Change (momentum)"""
    roc = ((close - close.shift(period)) / close.shift(period)) * 100
    return roc

def calculate_linear_slope(close, period=7):
    """Linear regression slope (% per day)"""
    def slope(y):
        if len(y) < 2:
            return 0
        x = np.arange(len(y))
        coeffs = np.polyfit(x, y, 1)
        return (coeffs[0] / y.iloc[-1]) * 100  # Normalize to percentage
    
    slopes = close.rolling(period).apply(slope, raw=False)
    return slopes

def calculate_rsi(close, period=7):
    """Relative Strength Index"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bb_width(close, period=10, std_dev=2):
    """Bollinger Band Width (%)"""
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    bb_width = ((upper - lower) / sma) * 100
    return bb_width

def calculate_distance_from_ma(close, period=5):
    """Price distance from moving average (%)"""
    ma = close.rolling(period).mean()
    distance = ((close - ma) / ma) * 100
    return distance

def calculate_high_low_range(high, low, close, period=5):
    """High-Low range as % of close"""
    high_max = high.rolling(period).max()
    low_min = low.rolling(period).min()
    hl_range = ((high_max - low_min) / close) * 100
    return hl_range


# ============================================================================
# MODEL A: SIMPLE VOLATILITY + MOMENTUM
# ============================================================================

def model_a_buy_gear(high, low, close):
    """
    Buy gear from ATR% (5-day)
    
    Thresholds:
    ATR% < 2%:   Gear 1 (-3%, very calm)
    ATR% < 3%:   Gear 2 (-4%)
    ATR% < 4%:   Gear 3 (-5%, default)
    ATR% < 5.5%: Gear 4 (-6%)
    ATR% >= 5.5%: Gear 5 (-7%, extreme)
    """
    atr_pct = calculate_atr_percent(high, low, close, period=5)
    
    def atr_to_gear(atr):
        if pd.isna(atr):
            return 3  # Default
        if atr < 2.0:
            return 1
        elif atr < 3.0:
            return 2
        elif atr < 4.0:
            return 3
        elif atr < 5.5:
            return 4
        else:
            return 5
    
    gear = atr_pct.apply(atr_to_gear)
    return gear, atr_pct

def model_a_sell_gear(high, low, close):
    """
    Sell gear from ROC (5-day) + ATR%
    
    Logic:
    - Base gear from ROC (momentum)
    - Adjust for volatility (ATR%)
    
    ROC thresholds (base):
    ROC > +10%:  Base 5 (strong up)
    ROC > +5%:   Base 4
    ROC > 0%:    Base 3 (default)
    ROC > -5%:   Base 2
    ROC <= -5%:  Base 1 (weak)
    
    ATR adjustment:
    High ATR (>4%) → -1 gear (more volatile, lower targets)
    """
    roc = calculate_roc(close, period=5)
    atr_pct = calculate_atr_percent(high, low, close, period=5)
    
    def roc_atr_to_gear(row):
        roc_val, atr_val = row
        
        if pd.isna(roc_val):
            return 3
        
        # Base from ROC
        if roc_val > 10:
            base = 5
        elif roc_val > 5:
            base = 4
        elif roc_val > 0:
            base = 3
        elif roc_val > -5:
            base = 2
        else:
            base = 1
        
        # Volatility adjustment
        if not pd.isna(atr_val) and atr_val > 4.0:
            base -= 1
        
        return max(1, min(5, base))
    
    gear = pd.DataFrame({'roc': roc, 'atr': atr_pct}).apply(roc_atr_to_gear, axis=1)
    return gear, roc, atr_pct


# ============================================================================
# MODEL B: SMOOTH TREND + REGIME
# ============================================================================

def model_b_buy_gear(high, low, close):
    """
    Buy gear from Historical Volatility (10-day)
    
    HV thresholds (annualized %):
    HV < 20%:  Gear 1 (very calm)
    HV < 35%:  Gear 2
    HV < 50%:  Gear 3 (default)
    HV < 70%:  Gear 4
    HV >= 70%: Gear 5 (extreme)
    """
    hv = calculate_historical_volatility(close, period=10)
    
    def hv_to_gear(h):
        if pd.isna(h):
            return 3
        if h < 20:
            return 1
        elif h < 35:
            return 2
        elif h < 50:
            return 3
        elif h < 70:
            return 4
        else:
            return 5
    
    gear = hv.apply(hv_to_gear)
    return gear, hv

def model_b_sell_gear(high, low, close):
    """
    Sell gear from Linear Slope (7-day) + Bollinger Width
    
    Slope thresholds (% per day):
    Slope > +2%/day:  Base 5
    Slope > +1%/day:  Base 4
    Slope > 0:        Base 3
    Slope > -1%/day:  Base 2
    Slope <= -1%/day: Base 1
    
    BB Width adjustment:
    High BB Width (>8%) → -1 gear (volatile regime)
    """
    slope = calculate_linear_slope(close, period=7)
    bb_width = calculate_bb_width(close, period=10)
    
    def slope_bb_to_gear(row):
        slope_val, bb_val = row
        
        if pd.isna(slope_val):
            return 3
        
        # Base from slope
        if slope_val > 2:
            base = 5
        elif slope_val > 1:
            base = 4
        elif slope_val > 0:
            base = 3
        elif slope_val > -1:
            base = 2
        else:
            base = 1
        
        # BB Width adjustment
        if not pd.isna(bb_val) and bb_val > 8.0:
            base -= 1
        
        return max(1, min(5, base))
    
    gear = pd.DataFrame({'slope': slope, 'bb': bb_width}).apply(slope_bb_to_gear, axis=1)
    return gear, slope, bb_width


# ============================================================================
# MODEL C: MEAN REVERSION FOCUS
# ============================================================================

def model_c_buy_gear(high, low, close):
    """
    Buy gear from ATR% (7-day)
    
    Similar to Model A but 7-day window (smoother)
    """
    atr_pct = calculate_atr_percent(high, low, close, period=7)
    
    def atr_to_gear(atr):
        if pd.isna(atr):
            return 3
        if atr < 2.0:
            return 1
        elif atr < 3.0:
            return 2
        elif atr < 4.0:
            return 3
        elif atr < 5.5:
            return 4
        else:
            return 5
    
    gear = atr_pct.apply(atr_to_gear)
    return gear, atr_pct

def model_c_sell_gear(high, low, close):
    """
    Sell gear from RSI (7-day) + Distance from 5MA
    
    Logic optimized for V-shaped rebounds:
    - RSI shows overbought/oversold
    - Distance from MA shows extension
    
    Combined score:
    RSI > 70 AND Distance > +3%:  Gear 5 (overbought, take profit)
    RSI > 60 OR Distance > +2%:   Gear 4
    RSI 40-60 AND Distance -1 to +1%: Gear 3 (default)
    RSI < 40 OR Distance < -2%:   Gear 2
    RSI < 30 AND Distance < -3%:  Gear 1 (oversold, low targets)
    """
    rsi = calculate_rsi(close, period=7)
    dist_ma = calculate_distance_from_ma(close, period=5)
    
    def rsi_dist_to_gear(row):
        rsi_val, dist_val = row
        
        if pd.isna(rsi_val) or pd.isna(dist_val):
            return 3
        
        # Combined logic
        if rsi_val > 70 and dist_val > 3:
            return 5
        elif rsi_val > 60 or dist_val > 2:
            return 4
        elif 40 <= rsi_val <= 60 and -1 <= dist_val <= 1:
            return 3
        elif rsi_val < 40 or dist_val < -2:
            return 2
        elif rsi_val < 30 and dist_val < -3:
            return 1
        else:
            return 3  # Default
    
    gear = pd.DataFrame({'rsi': rsi, 'dist': dist_ma}).apply(rsi_dist_to_gear, axis=1)
    return gear, rsi, dist_ma


# ============================================================================
# MODEL D: PURE GRAPH GEOMETRY
# ============================================================================

def model_d_buy_gear(high, low, close):
    """
    Buy gear from High/Low range % (5-day)
    
    No complex indicators, just price swings
    
    Range thresholds:
    Range < 3%:  Gear 1 (tight range)
    Range < 5%:  Gear 2
    Range < 7%:  Gear 3 (default)
    Range < 10%: Gear 4
    Range >= 10%: Gear 5 (wide swings)
    """
    hl_range = calculate_high_low_range(high, low, close, period=5)
    
    def range_to_gear(r):
        if pd.isna(r):
            return 3
        if r < 3:
            return 1
        elif r < 5:
            return 2
        elif r < 7:
            return 3
        elif r < 10:
            return 4
        else:
            return 5
    
    gear = hl_range.apply(range_to_gear)
    return gear, hl_range

def model_d_sell_gear(high, low, close):
    """
    Sell gear from ROC (5-day) + High/Low range %
    
    Similar to Model A but uses range instead of ATR
    """
    roc = calculate_roc(close, period=5)
    hl_range = calculate_high_low_range(high, low, close, period=5)
    
    def roc_range_to_gear(row):
        roc_val, range_val = row
        
        if pd.isna(roc_val):
            return 3
        
        # Base from ROC
        if roc_val > 10:
            base = 5
        elif roc_val > 5:
            base = 4
        elif roc_val > 0:
            base = 3
        elif roc_val > -5:
            base = 2
        else:
            base = 1
        
        # Range adjustment (high range = more volatile)
        if not pd.isna(range_val) and range_val > 7:
            base -= 1
        
        return max(1, min(5, base))
    
    gear = pd.DataFrame({'roc': roc, 'range': hl_range}).apply(roc_range_to_gear, axis=1)
    return gear, roc, hl_range


# ============================================================================
# MODEL E: COMPOSITE MULTI-FACTOR
# ============================================================================

def model_e_buy_gear(high, low, close):
    """
    Buy gear from weighted composite
    
    50% ATR%
    30% Historical Volatility
    20% BB Width
    
    Normalize each to 0-1, then map to gears 1-5
    """
    atr_pct = calculate_atr_percent(high, low, close, period=5)
    hv = calculate_historical_volatility(close, period=10)
    bb_width = calculate_bb_width(close, period=10)
    
    # Normalize each indicator to 0-1 scale
    def normalize(series, low, high):
        """Map [low, high] to [0, 1]"""
        return ((series - low) / (high - low)).clip(0, 1)
    
    atr_norm = normalize(atr_pct, 1.5, 6.0)     # 1.5% to 6% ATR
    hv_norm = normalize(hv, 15, 75)              # 15% to 75% HV
    bb_norm = normalize(bb_width, 3, 10)         # 3% to 10% BB width
    
    # Weighted composite
    composite = 0.5 * atr_norm + 0.3 * hv_norm + 0.2 * bb_norm
    
    def composite_to_gear(c):
        if pd.isna(c):
            return 3
        if c < 0.2:
            return 1
        elif c < 0.4:
            return 2
        elif c < 0.6:
            return 3
        elif c < 0.8:
            return 4
        else:
            return 5
    
    gear = composite.apply(composite_to_gear)
    return gear, composite

def model_e_sell_gear(high, low, close):
    """
    Sell gear from weighted composite
    
    40% ROC
    30% Linear Slope
    20% RSI
    10% Distance from MA
    
    Normalize and combine
    """
    roc = calculate_roc(close, period=5)
    slope = calculate_linear_slope(close, period=7)
    rsi = calculate_rsi(close, period=7)
    dist_ma = calculate_distance_from_ma(close, period=5)
    
    # Normalize to 0-1
    def normalize(series, low, high):
        return ((series - low) / (high - low)).clip(0, 1)
    
    roc_norm = normalize(roc, -10, 15)          # -10% to +15%
    slope_norm = normalize(slope, -2, 3)         # -2% to +3% per day
    rsi_norm = normalize(rsi, 20, 80)            # 20 to 80 RSI
    dist_norm = normalize(dist_ma, -5, 5)        # -5% to +5% from MA
    
    # Weighted composite
    composite = 0.4 * roc_norm + 0.3 * slope_norm + 0.2 * rsi_norm + 0.1 * dist_norm
    
    def composite_to_gear(c):
        if pd.isna(c):
            return 3
        if c < 0.2:
            return 1
        elif c < 0.4:
            return 2
        elif c < 0.6:
            return 3
        elif c < 0.8:
            return 4
        else:
            return 5
    
    gear = composite.apply(composite_to_gear)
    return gear, composite


# ============================================================================
# MAIN INTERFACE
# ============================================================================

MODELS = {
    'A': {
        'name': 'Simple Volatility + Momentum',
        'buy': model_a_buy_gear,
        'sell': model_a_sell_gear
    },
    'B': {
        'name': 'Smooth Trend + Regime',
        'buy': model_b_buy_gear,
        'sell': model_b_sell_gear
    },
    'C': {
        'name': 'Mean Reversion Focus',
        'buy': model_c_buy_gear,
        'sell': model_c_sell_gear
    },
    'D': {
        'name': 'Pure Graph Geometry',
        'buy': model_d_buy_gear,
        'sell': model_d_sell_gear
    },
    'E': {
        'name': 'Composite Multi-Factor',
        'buy': model_e_buy_gear,
        'sell': model_e_sell_gear
    }
}

def select_gears(model_name, high, low, close):
    """
    Main function to select buy and sell gears
    
    Parameters:
    -----------
    model_name : str ('A', 'B', 'C', 'D', or 'E')
    high, low, close : pd.Series (price data)
    
    Returns:
    --------
    dict with 'buy_gear', 'sell_gear', and diagnostic info
    """
    model = MODELS[model_name]
    
    buy_gear, buy_diag = model['buy'](high, low, close)
    sell_result = model['sell'](high, low, close)
    sell_gear = sell_result[0]
    sell_diag = sell_result[1:]
    
    return {
        'buy_gear': buy_gear,
        'sell_gear': sell_gear,
        'buy_diagnostic': buy_diag,
        'sell_diagnostic': sell_diag,
        'model_name': model['name']
    }
