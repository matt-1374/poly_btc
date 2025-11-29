import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from typing import Dict

def plot_timeline(df: pd.DataFrame, title: str) -> None:
    """Draws the Price vs Probability timeline using Matplotlib."""
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Turn on grid
    ax1.grid(True, alpha=0.3)

    # Left Axis: Prices
    color_btc = '#1f77b4'  # Blue
    ax1.plot(df['datetime'], df['btc_price'], color=color_btc, label='BTC Price', linewidth=1.5)
    
    # Strike Line
    strike = df['strike_price'].iloc[-1]
    ax1.axhline(strike, color='red', linestyle='--', alpha=0.7, label=f'Strike: {strike:,.0f}')
    
    ax1.set_ylabel('BTC Price ($)', color=color_btc, fontsize=12)
    ax1.tick_params(axis='y', labelcolor=color_btc)
    
    # Handle legend for ax1
    lines1, labels1 = ax1.get_legend_handles_labels()

    # Right Axis: Probability
    ax2 = ax1.twinx()
    color_poly = '#2ca02c'  # Green
    ax2.plot(df['datetime'], df['poly_yes_price'], color=color_poly, linewidth=2, label='Yes Price')
    
    ax2.set_ylabel('Prediction Probability', color=color_poly, fontsize=12)
    ax2.set_ylim(-0.05, 1.05)
    ax2.tick_params(axis='y', labelcolor=color_poly)

    # Combine legends
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    ax1.set_title(f'Timeline: {title}', fontsize=14, weight='bold')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    plt.tight_layout()
    plt.show()

def plot_sensitivity(df: pd.DataFrame, title: str) -> None:
    """Draws the S-Curve (Moneyness vs Probability) colored by time."""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.grid(True, alpha=0.3)

    # Scatter plot with colormap based on time progress
    sc = ax.scatter(
        df['moneyness'],
        df['poly_yes_price'],
        c=df['time_progress'],
        cmap='turbo',  # Spectral colormap
        s=20,
        alpha=0.6,
        edgecolors='none'
    )

    # Reference lines
    ax.axvline(0, color='black', linestyle='--', label='At The Money')
    ax.axhline(0.5, color='gray', linestyle=':', alpha=0.5)
    
    # Colorbar
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label('Time Progression', rotation=270, labelpad=15)

    ax.set_title(f'Sensitivity S-Curve: {title}', fontsize=14, weight='bold')
    ax.set_xlabel('Moneyness (BTC Price - Strike) [$]', fontsize=12)
    ax.set_ylabel('Implied Probability', fontsize=12)
    
    plt.tight_layout()
    plt.show()

def compare_events(events: Dict[str, pd.DataFrame]) -> None:
    """
    Draws a comparative scatter plot for multiple events using Matplotlib.
    Args:
        events: Dictionary mapping Label -> DataFrame
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.grid(True, alpha=0.3)
    
    # Standard color cycle for comparison
    colors = ['#2ca02c', '#ff7f0e', '#1f77b4', '#d62728']
    color_index = 0

    for label, df in events.items():
        color = colors[color_index % len(colors)]
        ax.scatter(
            df['moneyness'], 
            df['poly_yes_price'], 
            label=label, 
            color=color,
            s=20, 
            alpha=0.5,
            edgecolors='none'
        )
        color_index += 1

    ax.axvline(0, color='red', linestyle='--', label='Strike Price')
    ax.axhline(0.5, color='gray', linestyle=':', alpha=0.5)
    
    ax.set_title('Market Sensitivity Comparison', fontsize=14, weight='bold')
    ax.set_xlabel('Moneyness ($)')
    ax.set_ylabel('Probability')
    ax.legend()
    
    plt.tight_layout()
    plt.show()

def plot_aggregate_sensitivity(df: pd.DataFrame, title: str) -> None:
    """
    Plots an aggregated scatter plot of ALL events.
    X-Axis: Normalized Moneyness (0 = Strike).
    Color: Time Decay (Blue = Start/High Time, Red = End/No Time).
    """
    # 1. Reduced figsize (10, 6) prevents full-screen takeover.
    # 2. constrained_layout=True guarantees labels/titles fit inside the box.
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    
    ax.grid(True, alpha=0.3)

    # Scatter plot
    sc = ax.scatter(
        df['moneyness'],
        df['poly_yes_price'],
        c=df['time_progress'],
        cmap='jet',  # Blue -> Red
        s=5,
        alpha=0.4,
        edgecolors='none'
    )

    # Vertical line at Strike Price (0)
    ax.axvline(0, color='black', linestyle='--', linewidth=1.5, label='At The Money (Strike)')
    
    # Horizontal line at 50% probability
    ax.axhline(0.5, color='gray', linestyle=':', alpha=0.5)

    # Colorbar configuration
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label('Time Elapsed (Blue=Start, Red=End)', rotation=270, labelpad=20)
    
    # Labels
    ax.set_title(f'Aggregate Market Sensitivity: {title}', fontsize=14, weight='bold')
    ax.set_xlabel('Moneyness (BTC Price - Strike Price) [$]', fontsize=11)
    ax.set_ylabel('Prediction Probability (0.0 - 1.0)', fontsize=11)

    ax.legend(loc='upper left')
    
    plt.show()
