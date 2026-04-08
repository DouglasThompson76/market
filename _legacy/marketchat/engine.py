import pandas as pd
import duckdb
import os
import json
from typing import Dict, List, Optional

class MarketChatEngine:
    def __init__(self, snapshot_path: str, edge_path: str):
        self.snapshot_path = snapshot_path
        self.edge_path = edge_path
        self.db = duckdb.connect(database=':memory:') # Using in-memory DuckDB for edge analytics
        
        # Load snapshot into Pandas (it's only 12MB)
        print(f"Loading Snapshot from {snapshot_path}...")
        self.snapshot_df = pd.read_csv(snapshot_path)
        
        # Load Edge CSV into Pandas (258MB is fine for RAM)
        print(f"Loading Edge Data from {edge_path}...")
        try:
            self.edges_df = pd.read_csv(edge_path, on_bad_lines='skip', low_memory=False)
        except Exception as e:
            print(f"Error loading edges: {e}")
            self.edges_df = pd.DataFrame()
        
    def get_symbol_context(self, symbol: str) -> Optional[Dict]:
        """Fetch the full snapshot row for a symbol."""
        row = self.snapshot_df[self.snapshot_df['ticker'] == symbol]
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    def get_neighbors(self, symbol: str, limit: int = 20) -> List[Dict]:
        """Find immediate relationships for a symbol using the edge dataframe."""
        if self.edges_df.empty:
            return []
            
        results = self.edges_df[self.edges_df['src_symbol'] == symbol].head(limit)
        # Use where(pd.notnull(results), None) to handle NaNs for JSON compliance
        return results[['dst_symbol', 'dst_name', 'dst_entity_type', 'relation_code', 'weight', 'sign']].where(pd.notnull(results), None).to_dict('records')

    def simulate_shock(self, entity_id_or_macro: str, shock_value: float) -> pd.DataFrame:
        """
        Calculates ripple effect of a value change in a macro node or sector.
        """
        if self.edges_df.empty:
            return pd.DataFrame()

        # 1. Find all symbols directly connected to this macro/sector
        # Filter by dst_symbol or dst_name
        mask = (self.edges_df['dst_symbol'] == entity_id_or_macro) | (self.edges_df['dst_name'] == entity_id_or_macro)
        affected = self.edges_df[mask & (self.edges_df['src_entity_type'] == 'stock')].copy()
        
        if affected.empty:
            return pd.DataFrame()

        # 2. Join with the snapshot to get base gnn_prob
        merged = affected.merge(self.snapshot_df[['ticker', 'gnn_prob', 'selected_category']], 
                                left_on='src_symbol', right_on='ticker')
        
        # 3. Apply shock logic
        # New Prob = Current + (Shock * Weight * Sign)
        # Scaled to keep it within [0, 1]
        merged['simulated_prob'] = merged['gnn_prob'] + (shock_value * merged['weight'] * merged['sign'])
        merged['simulated_prob'] = merged['simulated_prob'].clip(0, 1)
        merged['delta'] = merged['simulated_prob'] - merged['gnn_prob']
        
        # Ensure result is JSON-safe by handling NaNs
        return merged.sort_values(by='delta', ascending=False).where(pd.notnull(merged), None)

if __name__ == "__main__":
    # Test runner
    SNAPSHOT = "MarketSnapshot_output.csv"
    EDGE_FILE = "edge/edges_9_types_2026-03-25_121026.csv"
    
    if os.path.exists(SNAPSHOT) and os.path.exists(EDGE_FILE):
        engine = MarketChatEngine(SNAPSHOT, EDGE_FILE)
        print("\n--- Test: HALLIBURTON Context ---")
        print(engine.get_symbol_context("HAL"))
        
        print("\n--- Test: Shocking 'Energy' ---")
        winners = engine.simulate_shock("Energy", 0.1)
        print(winners[['ticker', 'gnn_prob', 'simulated_prob', 'delta']].head(10))
    else:
        print("Required CSV files not found for testing.")
