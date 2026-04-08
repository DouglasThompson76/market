from marketchat.engine import MarketChatEngine
from marketchat.agent import MarketChatAgent
import json

engine = MarketChatEngine("MarketSnapshot_output.csv", "edge/edges_9_types_2026-03-25_121026.csv")
agent = MarketChatAgent(engine)

print("\n--- TEST: SIMULATION ---")
res = agent.handle_query("Simulate Energy +0.1")
print(json.dumps(res, indent=2))

print("\n--- TEST: SYMBOL LOOKUP ---")
res2 = agent.handle_query("Tell me about HAL")
print(json.dumps(res2, indent=2))
