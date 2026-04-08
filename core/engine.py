import pandas as pd
import glob
import os
from typing import Dict, List, Optional

class UnifiedMarketEngine:
    """
    Combined Data Engine for both MarketChat and MarketInfrastructure.
    Loads data once and maintains in-memory state for fast analytics.
    """
    def __init__(self, snapshot_root: str, root_snapshot_csv: str, edge_path: str):
        self.snapshot_root = snapshot_root
        self.root_snapshot_csv = root_snapshot_csv
        self.edge_path = edge_path
        self.metrics_cache = {} # {symbol: {metrics}}
        
        # 1. Load Root Snapshot (Inference & Ranking Store)
        print(f"Loading Root Snapshot from {root_snapshot_csv}...")
        self.root_df = pd.read_csv(root_snapshot_csv)
        
        # 2. Load Edge Data (Relation & Propagation Store)
        print(f"Loading Edge Data from {edge_path}...")
        try:
            self.edges_df = pd.read_csv(edge_path, on_bad_lines='skip', low_memory=False)
        except Exception as e:
            print(f"Error loading edges: {e}")
            self.edges_df = pd.DataFrame()

    # --- Infrastructure Logic ---
    def generate_candidates(self, min_prob: float = 0.6) -> pd.DataFrame:
        """Filters and ranks symbols from the root CSV for the Watchlist."""
        candidates = self.root_df[
            (self.root_df['gnn_prob'] > min_prob) & 
            (self.root_df['trading_action'].notnull())
        ].copy()
        return candidates.sort_values(by='gnn_prob', ascending=False)

    def compute_historical_metrics(self, symbols: List[str]) -> pd.DataFrame:
        """Scans snapshot/ to compute 20d High and 5d Avg Volume. Uses cache for speed."""
        
        # Only compute for symbols NOT in cache
        to_compute = [s for s in symbols if s not in self.metrics_cache]
        
        if to_compute:
            print(f"Cache miss for {len(to_compute)} symbols. Scanning historical snapshots...")
            all_snapshots = sorted(glob.glob(os.path.join(self.snapshot_root, "stock_snapshot_*.csv")), reverse=True)
            snapshots_20d = all_snapshots[:20]
            
            for symbol in to_compute:
                highs = []
                vols = []
                for snap_path in snapshots_20d:
                    try:
                        # Optimization: Get header once outside symbol loop if possible
                        # For now, keeping it robust
                        header = pd.read_csv(snap_path, nrows=0).columns.tolist()
                        col_map = {
                            'ticker': 'ticker',
                            'high': 'day_high' if 'day_high' in header else 'high' if 'high' in header else None,
                            'volume': 'day_volume' if 'day_volume' in header else 'volume' if 'volume' in header else None
                        }
                        use_cols = [v for v in col_map.values() if v]
                        
                        df_chunk = pd.read_csv(snap_path, usecols=use_cols, on_bad_lines='skip')
                        row = df_chunk[df_chunk['ticker'] == symbol]
                        if not row.empty:
                            if col_map['high']: highs.append(row[col_map['high']].iloc[0])
                            if col_map['volume']: vols.append(row[col_map['volume']].iloc[0])
                    except: continue
                
                if highs:
                    self.metrics_cache[symbol] = {
                        'ticker': symbol,
                        'resistance_20d': max(highs),
                        'avg_volume_5d': sum(vols[:5]) / len(vols[:5]) if vols else 0
                    }

        # Return from cache
        results = [self.metrics_cache[s] for s in symbols if s in self.metrics_cache]
        return pd.DataFrame(results)

    # --- Intelligence Logic (Chat) ---
    def get_symbol_context(self, symbol: str) -> Optional[Dict]:
        """Fetch the full snapshot row for a symbol."""
        row = self.root_df[self.root_df['ticker'] == symbol.upper()]
        if row.empty:
            return None
        return row.iloc[0].where(pd.notnull(row.iloc[0]), None).to_dict()

    def get_neighbors(self, symbol: str, limit: int = 20) -> List[Dict]:
        """Find immediate relationships for a symbol using the edge dataframe."""
        if self.edges_df.empty:
            return []
        results = self.edges_df[self.edges_df['src_symbol'] == symbol.upper()].head(limit)
        return results[['dst_symbol', 'dst_name', 'dst_entity_type', 'relation_code', 'weight', 'sign']].where(pd.notnull(results), None).to_dict('records')

    def simulate_shock(self, entity_id_or_macro: str, shock_value: float) -> pd.DataFrame:
        """Calculates ripple effect of a value change in a macro node or sector."""
        if self.edges_df.empty: return pd.DataFrame()
        mask = (self.edges_df['dst_symbol'] == entity_id_or_macro) | (self.edges_df['dst_name'] == entity_id_or_macro)
        affected = self.edges_df[mask & (self.edges_df['src_entity_type'] == 'stock')].copy()
        if affected.empty: return pd.DataFrame()
        merged = affected.merge(self.root_df[['ticker', 'gnn_prob', 'selected_category']], left_on='src_symbol', right_on='ticker')
        merged['simulated_prob'] = merged['gnn_prob'] + (shock_value * merged['weight'] * merged['sign'])
        merged['simulated_prob'] = merged['simulated_prob'].clip(0, 1)
        merged['delta'] = merged['simulated_prob'] - merged['gnn_prob']
        return merged.sort_values(by='delta', ascending=False).where(pd.notnull(merged), None)
