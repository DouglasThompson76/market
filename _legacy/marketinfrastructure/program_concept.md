AI-Powered Structural Breakout Trading Systems
build a high-probability, structural breakout system. use AI to remove administrative bottlenecks and operate with the efficiency of a hedge fund. use the @marketsnapshot_output.csv as the primary data source. the backup time series data is held in /snapshot folder for the last 90 days.

construct your system, integrating the "7 Favour Checks" and structural requirements.

1. The Market Dashboard
This prompt is designed for to capture the technical "Golden Hour" conditions while allowing for the manual inclusion of fundamental filters like SEC positioning and news.

Prompt: "Build a filter to identify high-probability structural breakout system from the 90 day snapshot data.

Core Technical Conditions: 
1. 30-Min Opening Range Break: Trigger when the price closes above the high of the 9:30–10:00 AM EST range [1, 5]. 
2. Volume Confirmation: Current bar volume must be 1.5x the average volume of the 30-minute range [5, 6]. 
3. Relative Volume: Daily volume must be greater than the 5-day Moving Average [User Requirement]. 
4. VWAP Filter: Price must be strictly above VWAP [5, 6]. 
5. Resistance Break: Price must break above the 20-day Resistance high [User Requirement]. 
6. Relative Strength: Include a filter where Stock RSI > Market RSI (using SPY as the proxy) and Price > Market/Sector Index. 
7. Time Constraint: Alerts should only fire before 11:30 AM EST [5, 6]. 

Output: HTML table with columns: Symbol, Price, Time, Volume, RSI, VWAP, Resistance, Relative Strength, Time Constraint, Alert Message. The symbol is a link to 1. Visual Entry. 2. is a link to 2. Programmed Exit. 3. is on top of page to analyse trades uploaded to folder /marketinfrastructure/trades

1. Visual Entry Requirements: 
* Plot the 30-min opening range high and the 20-day resistance line [5, 9]. 
* Mark triggers with a green triangle and a light green background [9, 10]. 
* Alert Message: Include Symbol, Price, Time, and a reminder to check 'SEC Positioning, Options Spikes, and News Narrative' before entry."
--------------------------------------------------------------------------------

2. The Programmed Exit: Two-Bar Trailing Stop
This script replaces emotional decision-making with a systematic process, ensuring your exits are based on market structure rather than fear [11-13].

Prompt: "Build a TradingView Pine Script V5 strategy for a structural two-bar trailing stop. 
> > Exit Logic: 
> > * Initial Stop: Set at the lowest low of the past two bars relative to the entry [14, 15]. 
> * Trailing Rule: Every time the price makes a new two-bar high (current high > high of past two bars), move the stop to the lowest low of the past two bars [14, 15]. 
> * Directional Constraint: The stop-line must only step up, never down [14, 16]. 
> > Visuals: Plot the stop line on the chart, color-coded red initially and green once it begins trailing [14, 16]."
--------------------------------------------------------------------------------

3. Post-Market AI Trade Autopsy & Meta-Coach
Upload the CSV data to be analysed for meta analysis.

By using "super prompting" at the end of the week, you can synthesize multiple autopsies to identify deep-seated blind spots [17-19].
Prompt: "Act as my AI Meta-Coach. I am pasting 10 individual trade autopsies from this week, which include my entry/exit rules and mental state [18, 19]. 
> > Your Task: 
> > 1. Conformance Audit: Analyze how often I strictly followed my 7 Favour Checks and the Two-Bar Trailing Stop [20, 21]. 
> 2. Identify Blind Spots: Look for patterns I am missing (e.g., 'inventing trades' or failing to account for sector tailwinds) [22, 23]. 
> 3. Quantify Costs: Estimate how much profit was lost due to rule violations [24]. > 4. Strategic Output: Provide one single objective for next week and a priority ranking of my top three mistakes to fix [19, 24]."
Key Execution Principles
Commit to Iteration: Do not expect these scripts to be perfect on the first try; plan to refine and test them over a two-week period [12, 25, 26].
Verification: Always verify the logic in a paper trading environment before using real capital, particularly for the automated trailing stop [12, 27].
Context is Everything: For the Autopsy, the more context you provide—such as your mental state during the trade—the more "surgical" the AI's coaching feedback will be [17, 27, 28].