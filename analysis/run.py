import os
import pandas as pd
import loader
import plotter

# --- Configuration ---
TARGET_DATE = "2025-11-28"

def main():
    # 1. Setup Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir) 
    
    print(f"Scanning for data in: {project_root}")

    try:
        # 2. Find all event folders
        event_folders = loader.get_event_folders(project_root, TARGET_DATE)
        print(f"Found {len(event_folders)} event folders for {TARGET_DATE}.")

        all_events_data = []

        # 3. Load EVERY folder found
        for folder in event_folders:
            market_event = loader.load_market_data(folder)
            
            if market_event is not None:
                # Add to our list
                all_events_data.append(market_event.df)
                print(f" Loaded: {folder.name} ({len(market_event.df)} rows)")

        # 4. Aggregate and Plot
        if all_events_data:
            print("\nMerging data...")
            # Combine all dataframes into one
            combined_df = pd.concat(all_events_data, ignore_index=True)
            
            print(f"Total Data Points: {len(combined_df):,}")
            print("Generating Aggregate Rainbow Chart...")
            
            plotter.plot_aggregate_sensitivity(
                combined_df, 
                title=f"All Events for {TARGET_DATE}"
            )
        else:
            print("No valid data found to plot.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
