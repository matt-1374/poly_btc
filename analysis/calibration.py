import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import loader
import os

# --- CONFIG ---
TARGET_DATE = "2025-11-28"
MIN_TRADES_PER_BUCKET = 5
JITTER_STRENGTH = 0.015

def get_outcome_for_event(df: pd.DataFrame) -> int:
    """Returns 1 if BTC ended above Strike, 0 otherwise."""
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

def plot_bucketed_calibration(df):
    # 1. Define Buckets
    price_bins = np.linspace(0, 1, 21)
    
    # Time Buckets (Inverted: High res near expiration)
    # Bins: 0-5, 5-10, 10-20, 20-40, 40+
    time_cutoffs = [0, 5, 10, 20, 40, 100]
    time_labels = ['0-5m (Expiring)', '5-10m (Late)', '10-20m (Transition)', '20-40m (Mid)', '40-60m (Early)']
    
    # 2. Assign Bins
    df['price_bin'] = pd.cut(df['poly_yes_price'], bins=price_bins)
    df['time_bucket'] = pd.cut(df['minutes_left'], bins=time_cutoffs, labels=time_labels)
    
    # 3. Aggregate
    grouped = df.groupby(['price_bin', 'time_bucket'], observed=False).agg(
        predicted_avg=('poly_yes_price', 'mean'),
        realized_win_rate=('actual_outcome', 'mean'),
        trade_count=('actual_outcome', 'count')
    ).reset_index()

    # 4. Filter and Clean
    data = grouped[grouped['trade_count'] >= MIN_TRADES_PER_BUCKET].dropna().copy()

    # --- 5. APPLY JITTER ---
    np.random.seed(42)
    data['x_plot'] = data['predicted_avg'] + np.random.uniform(-JITTER_STRENGTH, JITTER_STRENGTH, size=len(data))
    data['y_plot'] = data['realized_win_rate'] + np.random.uniform(-JITTER_STRENGTH, JITTER_STRENGTH, size=len(data))
    
    # Calculate sizes
    data['bubble_size'] = np.sqrt(data['trade_count']) * 15

    # --- PLOTTING ---
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.grid(True, alpha=0.3, linestyle='--')

    # Perfect Calibration Line
    ax.plot([0, 1], [0, 1], 'k--', alpha=0.4, linewidth=1.5, label="Perfect Calibration")

    # Define Colors (Red = Close to Expiry, Blue = Far)
    bucket_colors = {
        '0-5m (Expiring)':     '#d62728',  # Deep Red
        '5-10m (Late)':        '#ff7f0e',  # Orange
        '10-20m (Transition)': '#bcbd22',  # Yellow/Olive
        '20-40m (Mid)':        '#2ca02c',  # Green
        '40-60m (Early)':      '#1f77b4'   # Blue
    }

    # Plot each bucket
    for label in time_labels:
        subset = data[data['time_bucket'] == label]
        if subset.empty:
            continue
            
        ax.scatter(
            subset['x_plot'],
            subset['y_plot'],
            s=subset['bubble_size'],
            color=bucket_colors[label],
            alpha=0.65,
            edgecolors='white',
            linewidth=0.5,
            label=label
        )

    # Labels & Formatting
    ax.set_title(f"Calibration by Minutes Remaining (High Res End-Game): {TARGET_DATE}", fontsize=16, weight='bold')
    ax.set_xlabel("Market Price ($)", fontsize=12)
    ax.set_ylabel("Realized Win Rate (%)", fontsize=12)
    
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    
    # Legend
    ax.legend(title="Minutes to Expiry", loc='upper left', frameon=True)
    
    # Explanation
    ax.text(0.02, 0.78, "Red = Highest Gamma Risk", transform=ax.transAxes, fontsize=10, color='#d62728',
             bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray'))

    plt.tight_layout()
    
    # Save
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    filename = f"calibration_endgame_focus_{TARGET_DATE}.pdf"
    plt.savefig(os.path.join(desktop_path, filename))
    print(f"✅ Plot saved to: {filename}")
    
    plt.show()

# --- EXECUTION ---
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    print("Loading data...")
    df = build_granular_data(project_root, TARGET_DATE)
    
    if not df.empty:
        plot_bucketed_calibration(df)
    else:
        print("No data found.")
