import re
from typing import Dict, List, Optional
from core.engine import UnifiedMarketEngine

class UnifiedMarketAgent:
    def __init__(self, engine: UnifiedMarketEngine):
        self.engine = engine
        self.stop_words = {'tell', 'show', 'what', 'know', 'about', 'this', 'that', 'with', 'me'}

    def handle_query(self, text: str) -> Dict:
        """Main entry point for unified natural language processing."""
        text_lower = text.lower()
        
        # 1. Simulation Detect
        if "simulate" in text_lower:
            return self._handle_simulation(text_lower)
        
        # 2. Symbol Lookup Detect
        symbol = self._extract_symbol(text)
        if symbol:
            return self._handle_symbol_lookup(symbol)
            
        return {
            "type": "error",
            "message": f"I'm not sure how to handle '{text}'. Try 'Simulate Oil +0.2' or 'Tell me about $HAL'."
        }

    def _extract_symbol(self, text: str) -> Optional[str]:
        # Priority 1: Prefix with $
        symbol_match = re.search(r'\$([A-Z]{1,5})\b', text)
        if symbol_match: return symbol_match.group(1)
        
        # Priority 2: Uppercase word of 1-5 chars that isn't a stop word
        potential_symbols = re.findall(r'\b([A-Z]{1,5})\b', text)
        for s in potential_symbols:
            if s.lower() not in self.stop_words:
                return s
        return None

    def _handle_simulation(self, text: str) -> Dict:
        match = re.search(r'simulate\s+([\w\s]+)\b[\s\+-]*([\d\.]+(?:%?))', text)
        if not match:
            return {"type": "error", "message": "Format: 'Simulate [Name] [Value]' (e.g., 'Simulate Oil 0.15')"}
        entity = match.group(1).strip().capitalize()
        value_str = match.group(2).replace('%', '')
        try:
            value = float(value_str)
            if '%' in match.group(2): value /= 100.0
        except: return {"type": "error", "message": "Invalid simulation value."}
        
        winners = self.engine.simulate_shock(entity, value)
        if winners.empty: return {"type": "error", "message": f"No data for influencer '{entity}'."}
        return {
            "type": "simulation_result",
            "entity": entity,
            "value": value,
            "results": winners.head(10).to_dict('records')
        }

    def _handle_symbol_lookup(self, symbol: str) -> Dict:
        context = self.engine.get_symbol_context(symbol)
        if not context: return {"type": "error", "message": f"Symbol {symbol} not found."}
        neighbors = self.engine.get_neighbors(symbol)
        return {
            "type": "symbol_report",
            "symbol": symbol,
            "context": context,
            "influence_network": neighbors
        }
