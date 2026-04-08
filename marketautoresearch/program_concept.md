The repo is intentionally minimal:



\* `prepare.py` → data setup

\* `train.py` → \*\*ONLY file the AI edits\*\*

\* `program.md` → rules + instructions


Think of this like \*\*pokemon evolution\*\*:



```

mutation → test → keep if better → repeat

```



\* Each run = one “mutation”

\* Metric = fitness function

\* Bad changes = deleted automatically



This loop can run \*\*8–12 experiments per hour\*\* (\[thecreatorsai.com]\[1])



\---



\# ⚡ 6. Example: What you actually tell the AI



You don’t code—you give a \*\*research instruction\*\*, e.g.:



```

Goal: Improve validation loss



Constraints:

\- Only modify train.py

\- Keep runtime under 5 minutes

\- Do not increase model size drastically



Ideas:

\- Try different optimizers

\- Adjust learning rate schedules

```



The agent handles everything else.



\---



\# 🚀 7. Fastest way to get value (practical advice)



Given your background (trading + ML systems), the best use cases are:



\### 🔹 A. Model optimisation



\* Tune your GNN training loop

\* Optimise loss / convergence



\### 🔹 B. Strategy discovery



\* Let it experiment with:



&#x20; \* feature engineering

&#x20; \* signal transformations

&#x20; \* risk weighting logic



\### 🔹 C. Edge discovery (very relevant to you)



\* Use it to:



&#x20; \* modify scoring functions

&#x20; \* test filters automatically

&#x20; \* evolve alpha signals



\---



\# ⚠️ 8. Common pitfalls



\* ❌ Weak prompt → random/unproductive experiments - avoid wasting time

\* ❌ Too much freedom → agent breaks training

\* ❌ No clear metric → useless optimisation



\---



\# 🧩 9. Key insight (why this matters)



This is \*\*not AutoML\*\*.



\* AutoML → tunes parameters

\* Autoresearch → \*\*rewrites the system itself\*\*



That’s why it’s powerful:



\* It can change architecture

\* It can change logic

\* It can discover non-obvious improvements, patterns humans can't find



\---


\# 🧱 1. Required Architecture (Critical)



You must mirror autoresearch’s \*\*3 constraints\*\*:



\### ✅ A. Frozen environment (DO NOT TOUCH)



\* Market data

\* Snapshots

\* Edge file generation

\* Evaluation logic



👉 This ensures comparability across experiments (\[philschmid.de]\[1])



\---



\### ✅ B. Single editable file (VERY IMPORTANT)



👉 Create:



```bash

program.py

```



ONLY this file is modifiable by the AI.



Inside it:



\* feature transformations

\* scoring logic

\* signal generation

\* risk rules



\---



\### ✅ C. Fixed evaluation budget



Example:



\* snapshots = last 60 days

\* Max runtime = 60 seconds




\---



\# ⚙️ 2. Your New Pipeline (Concrete Design)



\## 🔄 Full loop



```python

while True:

&#x20;   modify(program.py)

&#x20;   run\_????()

&#x20;   score = evaluate()



&#x20;   if score > best\_score:

&#x20;       commit()

&#x20;   else:

&#x20;       revert()

```



Use the autoresearch pattern:



\* edit → run → evaluate → keep/revert (\[Data Science Dojo]\[2])



\---



\# 📊 3. Define Your Objective Function (MOST IMPORTANT)



You must define a \*\*single scalar metric\*\*.



\### ❌ WRONG



\* “good trades”

\* “better signals”



\### ✅ CORRECT (example)



```python

score = (

&#x20;   total\_return \* 0.5

&#x20;   + sharpe\_ratio \* 0.3

&#x20;   - max\_drawdown \* 0.2

)

```



Or more aggressive (fits your style):



```python

score = (

&#x20;   profit\_factor \* 0.4

&#x20;   + win\_rate \* 0.2

&#x20;   - max\_drawdown \* 0.4

)

```



👉 This is your \*\*fitness function\*\*



\---



\# 🧠 4. What the AI Should Be Allowed to Modify



Inside `program.py`, allow ONLY:



\### 🔹 Feature transformations



```python

momentum = log\_return\_5d \* 1.5

volatility\_adj = atr / price

```



\---



\### 🔹 Signal logic



```python

if rsi > 60 and macd\_hist > 0:

&#x20;   signal = 1

```



\---



\### 🔹 Scoring



```python

score = (

&#x20;   momentum \* 0.4 +

&#x20;   volume\_trend \* 0.3 -

&#x20;   volatility \* 0.3

)

```



\---



\### 🔹 Risk rules (VERY important for you)



```python

stop\_loss = entry\_price \* (1 - atr \* 1.2)

take\_profit = entry\_price \* (1 + atr \* 2.5)

```



\---



\# 🚀 5. Apply to Your GNN System



\## 🔗 Where autoresearch fits



Your current pipeline:



```

Snapshots → Graph → GNN → Predictions → Filters → Trades

```



\### Insert autoresearch here:



```

Snapshots → Graph → GNN → Predictions

&#x20;                              ↓

&#x20;                     strategy.py (AI edits)

&#x20;                              ↓

&#x20;                       Backtest + Score

```



\---



\# ⚡ 6. High-Impact Use Cases for YOU



\## 🧪 A. Feature discovery (huge edge)



Let AI test:



\* new node features

\* rolling windows (10d vs 20d vs 60d)

\* volatility normalisation



\---



\## 🔗 B. Edge weighting optimisation



AI modifies:



```python

sector\_weight = 0.44

fundamental\_weight = 0.30

correlation\_weight = 0.26

```



👉 This directly impacts your GNN



\---



\## 🎯 C. Selection filter evolution



Your current:



```python

ALL signals == 1

```



AI can discover:



\* probabilistic thresholds

\* partial signal combinations

\* regime-based filters



\---



\## 🛡️ D. Risk management (your biggest gap)



AI can evolve:



\* dynamic stop loss (ATR / volatility based)

\* trailing exits

\* regime exits (trend breakdown)



\---



\# 🧠 7. Prompt You Should Use (Optimised for YOU)



Use this with your coding agent:



\---



\### 🔥 AUTORESEARCH PROMPT (TRADING VERSION)



```

You are an autonomous quantitative research agent.



Goal:

Maximise trading performance using the score function.



Constraints:

\- ONLY modify strategy.py

\- Do NOT modify data pipeline or evaluation

\- Keep runtime under 60 seconds

\- Avoid overfitting (prefer generalisable logic)



You may:

\- Adjust feature transformations

\- Modify signal conditions

\- Change scoring weights

\- Improve risk management rules



You must:

\- Propose one change at a time

\- Explain reasoning briefly

\- Run backtest

\- Compare score vs previous

\- Keep change ONLY if score improves



Focus areas:

\- Risk-adjusted return

\- Drawdown reduction

\- Trend continuation

\- Avoiding false breakouts



If error occurs:

\- Fix and retry

\- If repeated failure, revert and try different idea

```



\---



\# ⚠️ 8. Critical Pitfalls (Specific to YOU)



\## ❌ Overfitting (BIG RISK)



\* AI will optimise to last 60 days

\* Solution:



&#x20; \* rotate time windows

&#x20; \* use multiple test periods



\---



\## ❌ Signal collapse



\* AI may converge to “no trades”

\* Fix:



```python

min\_trades\_penalty = -10 if trades < 20 else 0

```



\---



\## ❌ Excessive risk



\* AI may maximise returns via leverage

\* Fix:



```python

if max\_drawdown > 0.15:

&#x20;   reject\_strategy()

```



\---



\# 🧩 9. Advanced (Next Level for You)



\## 🔥 Multi-agent autoresearch



Run:



\* Agent 1 → feature discovery

\* Agent 2 → risk optimisation

\* Agent 3 → execution logic



Then combine best outputs.



\---



\## 🔥 Graph-level autoresearch



Let AI modify:



\* edge creation rules

\* correlation thresholds

\* macro node influence



\---



\# ✅ Bottom Line



You are essentially turning your system into:



> \*\*A self-improving trading engine\*\*



Exactly like Karpathy’s idea:



\* AI edits system

\* tests it

\* keeps improvements

\* runs continuously overnight (\[Data Science Dojo]\[2])



\---



\# 👉 If you want next step

snapshot folder contains 90 days of market data files
marketsnapshot_output.csv was generated following training the GNN model