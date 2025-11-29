import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import loader
import os

# --- CONFIG ---
TARGET_DATE = "2025-11-28"
MIN_TRADES_PER_BUCKET = 5 
JITTER_STRENGTH = 0.015  # How much to spread the dots (0.015 = 1.5% variance)

def get_outcome_for_event(df: pd.DataFrame) -> int:
    last_row = df.iloc[-1]
    if last_row['btc_price'] >= last_row['strike_price']:
        return 1
    return 0

def build_granular_data(project_root, date_str):
    all_trades = []
    try:
        event_folders = loader.get_event_folders(project_root, date_str)
    except FileNotFoundError:
        print(f"Error: Data not found for {date_str}")
        return pd.DataFrame()

    print(f"Scanning {len(event_folders)} events...")

    for folder in event_folders:
        market_event = loader.load_market_data(folder)
        if market_event is None: continue
        
        df = market_event.df
        outcome = get_outcome_for_event(df)
        
        end_time = df['timestamp'].max()
        df['minutes_left'] = (end_time - df['timestamp']) / 60
        df['actual_outcome'] = outcome
        
        all_trades.append(df[['poly_yes_price', 'actual_outcome', 'minutes_left']])

    return pd.concat(all_trades) if all_trades else pd.DataFrame()

def plot_rainbow_calibration(df):
    # 1. Create Granular Bins
    price_bins = np.linspace(0, 1, 21)
    time_bins = np.linspace(0, 60, 31)
    
    # 2. Assign Bins
    df['price_bin'] = pd.cut(df['poly_yes_price'], bins=price_bins)
    df['time_bin'] = pd.cut(df['minutes_left'], bins=time_bins)
    
    # 3. Aggregate
    grouped = df.groupby(['price_bin', 'time_bin'], observed=False).agg(
        predicted_avg=('poly_yes_price', 'mean'),
        realized_win_rate=('actual_outcome', 'mean'),
        trade_count=('actual_outcome', 'count'),
        time_avg=('minutes_left', 'mean')
    ).reset_index()

    # 4. Filter and Clean
    data = grouped[grouped['trade_count'] >= MIN_TRADES_PER_BUCKET].dropna().copy()

    # --- 5. APPLY JITTER ---
    # This adds random noise to X and Y to separate overlapping points
    # We use a reproducible seed for consistent visuals
    np.random.seed(42)
    
    # Jitter X (Price)
    data['x_plot'] = data['predicted_avg'] + np.random.uniform(-JITTER_STRENGTH, JITTER_STRENGTH, size=len(data))
    
    # Jitter Y (Win Rate)
    data['y_plot'] = data['realized_win_rate'] + np.random.uniform(-JITTER_STRENGTH, JITTER_STRENGTH, size=len(data))

    # --- PLOTTING ---
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.grid(True, alpha=0.3, linestyle='--')

    # Perfect Calibration Line
    ax.plot([0, 1], [0, 1], 'k--', alpha=0.3, linewidth=1.5, label="Perfect Calibration")

    # Smart Sizing: Square Root scaling
    sizes = np.sqrt(data['trade_count']) * 15

    scatter = ax.scatter(
        data['x_plot'],
        data['y_plot'],
        c=data['time_avg'],
        cmap='jet_r', 
        s=sizes,
        alpha=0.60,         # Lower alpha to see through the clusters
        edgecolors='none'   # Remove edges to reduce visual noise
    )

    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Minutes Remaining (Blue=60m, Red=0m)', rotation=270, labelpad=20)

    # Labels
    ax.set_title(f"Calibration Rainbow (Jittered): {TARGET_DATE}", fontsize=16, weight='bold')
    ax.set_xlabel("Market Price ($)", fontsize=12)
    ax.set_ylabel("Realized Win Rate (%)", fontsize=12)
    
    # Padded Axes so dots don't get cut off
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    
    # Explanation Text
    ax.text(0.02, 0.95, "• Points Jittered (±1.5%) to reduce overlap\n• Size $\propto \sqrt{Volume}$", 
            transform=ax.transAxes, fontsize=10,
            bbox=dict(facecolor='white', alpha=0.9, edgecolor='gray', boxstyle='round'))

    plt.tight_layout()
    
    # Save
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    filename = f"rainbow_calibration_{TARGET_DATE}_jittered.pdf"
    plt.savefig(os.path.join(desktop_path, filename))
    print(f"✅ Chart saved to: {filename}")
    
    plt.show()

# --- EXECUTION ---
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    print("Loading data...")
    df = build_granular_data(project_root, TARGET_DATE)
    
    if not df.empty:
        plot_rainbow_calibration(df)
    else:
        print("No data found.")
