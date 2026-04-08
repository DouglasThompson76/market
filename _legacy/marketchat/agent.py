import re
from typing import Dict, List, Optional
from marketchat.engine import MarketChatEngine

class MarketChatAgent:
    def __init__(self, engine: MarketChatEngine):
        self.engine = engine
        
    def handle_query(self, text: str) -> Dict:
        """Main entry point for natural language processing."""
        # 1. Check for Simulation (e.g., "Simulate oil +10%")
        if "simulate" in text.lower():
            return self._handle_simulation(text.lower())
        
        # 2. Check for Symbol Lookup (e.g., "Tell me about HAL")
        # Try to find $TICKER or UPPERCASE TICKER or word in snapshot
        # Exclude common stop words
        stop_words = {'tell', 'show', 'what', 'know', 'about', 'this', 'that', 'with'}
        
        # Priority 1: Prefix with $
        symbol_match = re.search(r'\$([A-Z]{1,5})\b', text)
        if not symbol_match:
            # Priority 2: Uppercase word of 1-5 chars that isn't a stop word
            potential_symbols = re.findall(r'\b([A-Z]{1,5})\b', text)
            symbol = None
            for s in potential_symbols:
                if s.lower() not in stop_words:
                    symbol = s
                    break
        else:
            symbol = symbol_match.group(1)

        if symbol:
            return self._handle_symbol_lookup(symbol)
            
        # 3. Check for Macro Analysis (e.g., "Why is Tech bullish?")
        # (Simplified to a few keywords for v1)
        if "tech" in text or "energy" in text or "oil" in text:
            return self._handle_macro_query(text)
            
        return {
            "type": "error",
            "message": f"I'm not sure how to handle '{text}'. Try 'Simulate Oil +0.2' or 'Tell me about HAL'."
        }

    def _handle_simulation(self, text: str) -> Dict:
        # Simple extraction: "Simulate [Entity] [Charge]"
        # Regex to find a word followed by a plus/minus number
        match = re.search(r'simulate\s+([\w\s]+)\b[\s\+-]*([\d\.]+(?:%?))', text)
        if not match:
            return {"type": "error", "message": "Format should be 'Simulate [Name] [Value]' (e.g., 'Simulate Oil 0.15')"}
            
        entity = match.group(1).strip().capitalize()
        value_str = match.group(2).replace('%', '')
        try:
            value = float(value_str)
            # If percentage, convert to decimal
            if '%' in match.group(2):
                value /= 100.0
        except ValueError:
            return {"type": "error", "message": "Invalid simulation value."}

        winners = self.engine.simulate_shock(entity, value)
        
        if winners.empty:
            return {"type": "error", "message": f"No data found for influencer '{entity}'."}
            
        return {
            "type": "simulation_result",
            "entity": entity,
            "value": value,
            "results": winners.head(10).to_dict('records')
        }

    def _handle_symbol_lookup(self, symbol: str) -> Dict:
        context = self.engine.get_symbol_context(symbol)
        if not context:
            return {"type": "error", "message": f"Symbol {symbol} not found in current snapshot."}
            
        neighbors = self.engine.get_neighbors(symbol)
        
        return {
            "type": "symbol_report",
            "symbol": symbol,
            "context": context,
            "influence_network": neighbors
        }

    def _handle_macro_query(self, text: str) -> Dict:
        # This would normally use a GNN traversal. For now, a simple placeholder.
        return {
            "type": "macro_report",
            "message": "This feature is currently being evolved by the Autoresearch agent."
        }
