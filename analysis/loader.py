import pandas as pd
from pathlib import Path
from typing import List, Optional, Union
from dataclasses import dataclass

@dataclass
class MarketEvent:
    """Data structure to hold event details and the processed dataframe."""
    event_id: str       # e.g., "0500_bitcoin-..."
    date: str           # e.g., "2025-11-28"
    df: pd.DataFrame    # The processed market data

def get_event_folders(base_dir: Union[str, Path], date_str: str) -> List[Path]:
    """
    Scans the date directory and returns a list of Paths to specific event folders.
    """
    date_path = Path(base_dir) / "data_collection" / date_str
    
    if not date_path.exists():
        raise FileNotFoundError(f"Date folder not found: {date_path}")

    # Return sorted path objects for directories, ignoring hidden files
    return sorted([
        p for p in date_path.iterdir() 
        if p.is_dir() and not p.name.startswith('.')
    ])

def load_market_data(folder_path: Path) -> Optional[MarketEvent]:
    """
    Reads 'market_data.csv' from a folder, processes it, and returns a MarketEvent object.
    """
    csv_path = folder_path / "market_data.csv"
    
    if not csv_path.exists():
        print(f"CSV missing in: {folder_path.name}")
        return None

    try:
        df = pd.read_csv(csv_path)

        # --- Data Processing ---
        # 1. Time conversion
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')

        # 2. Filter invalid rows (where strike is 0)
        df = df[df['strike_price'] > 100].copy()

        if df.empty:
            return None

        # 3. Calculate Moneyness (Underlying Price - Strike Price)
        df['moneyness'] = df['btc_price'] - df['strike_price']

        # 4. Calculate Time Progress (0.0 start -> 1.0 end) for visualization gradients
        min_t = df['timestamp'].min()
        max_t = df['timestamp'].max()
        if max_t > min_t:
            df['time_progress'] = (df['timestamp'] - min_t) / (max_t - min_t)
        else:
            df['time_progress'] = 0.0

        # Return the structured data
        return MarketEvent(
            event_id=folder_path.name,
            date=folder_path.parent.name,
            df=df
        )

    except Exception as e:
        print(f"Error loading {folder_path.name}: {e}")
        return None
