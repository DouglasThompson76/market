import pandas as pd
import glob
import os
from typing import Dict, List, Optional

class InfrastructureDataCore:
    def __init__(self, snapshot_root: str, root_snapshot_csv: str):
        self.snapshot_root = snapshot_root
        self.root_snapshot_csv = root_snapshot_csv
        
        # 1. Load the main screening/ranking source
        print(f"Loading Root Snapshot from {root_snapshot_csv}...")
        self.root_df = pd.read_csv(root_snapshot_csv)
        
    def generate_candidates(self) -> pd.DataFrame:
        """
        Filters and ranks symbols from the root CSV to create the primary watchlist.
        """
        # Filter for high-probability candidates
        # (Using gnn_prob and presence of a recommended action)
        candidates = self.root_df[
            (self.root_df['gnn_prob'] > 0.6) & 
            (self.root_df['trading_action'].notnull())
        ].copy()
        
        # Build initial candidate list
        return candidates.sort_values(by='gnn_prob', ascending=False)

    def compute_historical_metrics(self, symbols: List[str]) -> pd.DataFrame:
        """
        Scans all files in snapshot/ to compute 20d High and 5d Avg Volume for symbols.
        """
        print(f"Scanning historical snapshots in {self.snapshot_root}...")
        
        # Find all snapshot CSV files and sort from newest to oldest
        all_snapshots = sorted(glob.glob(os.path.join(self.snapshot_root, "stock_snapshot_*.csv")), reverse=True)
        
        # We only need the last 20 for resistance and last 5 for volume
        snapshots_20d = all_snapshots[:20]
        
        results = []
        for symbol in symbols:
            symbol_data = []
            for i, snap_path in enumerate(snapshots_20d):
                try:
                    # Using a subset of the file to save memory
                    it = pd.read_csv(snap_path, chunksize=1000)
                    row = None
                    for chunk in it:
                        match = chunk[chunk['ticker'] == symbol]
                        if not match.empty:
                            row = match.iloc[0]
                            break
                    
                    if row is not None:
                        symbol_data.append({
                            'date': snap_path,
                            'high': row.get('day_high', row.get('high', 0)),
                            'volume': row.get('day_volume', row.get('volume', 0)),
                            'close': row.get('day_close', row.get('close', 0))
                        })
                except Exception as e:
                    continue
            
            # Compute rolling metrics
            if symbol_data:
                df = pd.DataFrame(symbol_data)
                res_20d = df['high'].max()
                avg_vol_5d = df['volume'].head(5).mean()
                results.append({
                    'ticker': symbol,
                    'resistance_20d': res_20d,
                    'avg_volume_5d': avg_vol_5d,
                    'current_price': symbol_data[0]['close']
                })
        
        return pd.DataFrame(results)

if __name__ == "__main__":
    core = InfrastructureDataCore("snapshot", "MarketSnapshot_output.csv")
    cands = core.generate_candidates().head(5)
    print("\n--- Top Candidates ---")
    print(cands[['ticker', 'gnn_prob', 'trading_action']])
    
    metrics = core.compute_historical_metrics(cands['ticker'].tolist())
    print("\n--- Historical Metrics (20d Resistance / 5d Vol) ---")
    print(metrics)
