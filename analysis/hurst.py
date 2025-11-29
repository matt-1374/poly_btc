import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# --- IMPORT ---
from loader import get_event_folders, load_market_data

# --- CONFIG ---
TARGET_DATE = "2025-11-28"
# We need a larger window for Returns to get a stable signal
HURST_WINDOW = 1000  
MIN_CHUNK_SIZE = 50

def get_hurst_exponent_on_returns(prices):
    """
    Calculates H on Log Returns.
    """
    # 1. Convert Price to Log Returns (Differencing)
    # This removes the "Drift" and leaves the "Noise/Signal"
    prices = np.array(prices)
    if len(prices) < 2: return 0.5
    
    # Log Returns: ln(P_t / P_t-1)
    returns = np.diff(np.log(prices))
    
    if len(returns) < 100:
        return 0.5

    # 2. Standard R/S Analysis on the Returns
    series = returns
    
    min_log = np.log10(MIN_CHUNK_SIZE)
    max_log = np.log10(len(series))
    scales = np.unique(np.logspace(min_log, max_log, num=10).astype(int))
    scales = scales[scales < len(series) // 2]
    
    if len(scales) < 3:
        return 0.5

    rs_values = []

    for n in scales:
        num_chunks = len(series) // n
        chunks = np.array_split(series[:num_chunks * n], num_chunks)
        rs_for_chunks = []
        
        for chunk in chunks:
            mean = np.mean(chunk)
            y = chunk - mean
            z = np.cumsum(y)
            r = np.max(z) - np.min(z)
            s = np.std(chunk)
            
            if s == 0: continue
            rs_for_chunks.append(r / s)
        
        if rs_for_chunks:
            rs_values.append(np.mean(rs_for_chunks))

    if len(rs_values) != len(scales):
        return 0.5

    try:
        slope, _ = np.polyfit(np.log10(scales), np.log10(rs_values), 1)
        return slope
    except:
        return 0.5

def calculate_rolling_hurst(df, window):
    print(f"Calculating Rolling Hurst on Returns (Window={window})...")
    
    hurst_values = [np.nan] * window
    prices = df['btc_price'].values
    
    # Optimization: Pre-calculate indices to avoid list slicing overhead
    # But for clarity, we stick to the simple loop
    for i in range(window, len(prices)):
        # Pass the raw price slice; the function handles conversion to returns
        slice_data = prices[i-window : i]
        h = get_hurst_exponent_on_returns(slice_data)
        hurst_values.append(h)
        
        if i % 5000 == 0:
            print(f"Processing row {i}/{len(prices)}...")
            
    df['Hurst'] = hurst_values
    return df

def plot_market_regime(df):
    # Filter out NaN (startup window)
    plot_df = df.dropna(subset=['Hurst'])
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, 
                                   gridspec_kw={'height_ratios': [2, 1]})
    
    # Top: Price
    ax1.plot(plot_df['datetime'], plot_df['btc_price'], color='black', alpha=0.6, label='BTC Price', lw=1)
    ax1.set_ylabel('BTC Price ($)')
    ax1.set_title(f"Market Regime Corrected (Log-Return Hurst): {TARGET_DATE}", fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    y_min, y_max = ax1.get_ylim()
    
    # Color Bands (Updated Thresholds for Returns)
    # H on returns usually oscillates closer to 0.5
    # > 0.6 is a VERY strong trend. < 0.4 is mean reversion.
    ax1.fill_between(plot_df['datetime'], y_min, y_max, 
                     where=(plot_df['Hurst'] > 0.55), color='green', alpha=0.15, label='Trending (H > 0.55)')
    ax1.fill_between(plot_df['datetime'], y_min, y_max, 
                     where=(plot_df['Hurst'] < 0.45), color='red', alpha=0.15, label='Mean Reverting (H < 0.45)')
    ax1.legend(loc='upper left')

    # Bottom: Hurst
    ax2.plot(plot_df['datetime'], plot_df['Hurst'], color='blue', lw=1)
    ax2.axhline(0.5, color='black', linestyle='--', label='Random Walk (0.5)')
    ax2.axhline(0.55, color='green', linestyle=':', alpha=0.5)
    ax2.axhline(0.45, color='red', linestyle=':', alpha=0.5)
    
    ax2.set_ylabel('Hurst Exponent (on Returns)')
    ax2.set_xlabel('Time')
    ax2.set_ylim(0.2, 0.8) # Focus on the realistic range
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    plt.tight_layout()
    
    # Save
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    plt.savefig(os.path.join(desktop, f"regime_hurst_corrected_{TARGET_DATE}.pdf"))
    print("✅ Plot saved to Desktop.")
    plt.show()

# --- MAIN ---
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    try:
        event_folders = get_event_folders(project_root, TARGET_DATE)
        all_dfs = []
        
        print(f"Scanning {len(event_folders)} folders...")
        for folder in event_folders:
            market_event = load_market_data(folder)
            if market_event:
                all_dfs.append(market_event.df)
        
        if all_dfs:
            full_df = pd.concat(all_dfs).sort_values('timestamp').reset_index(drop=True)
            
            # Subsample (Every 5th row) to keep data granular but faster
            analysis_df = full_df.iloc[::5].copy().reset_index(drop=True)
            
            # Run Analysis
            df_result = calculate_rolling_hurst(analysis_df, window=HURST_WINDOW)
            
            # Plot
            plot_market_regime(df_result)
        else:
            print("No data loaded.")

    except Exception as e:
        print(f"Error: {e}")
