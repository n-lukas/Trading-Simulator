# Trading Simulator

This is a browser-based trading simulator that allows users to trade a small set of fictional equities while prices update in real time. The application runs entirely client-side and is designed to be embedded directly into a portfolio site.

Users can take both long and short positions, track portfolio value over time, and see how changes in price affect overall account value.

## Creation
- This game was designed for and can be tested on my [portfolio](https://nicholaslukas.com)
- This game is made primarily in python to be hosted on a liveserver. It uses java for the charts. The intent is to show off python skills, web development skills, and financial acumen. 

## Story
You were given an interest-free margin loan of $10,000 to trade with. The condition for this is that you must 10x the amount that was given to you. If your portfolio value ever hits 0 you failed.

## Game Overview

- You start with a fixed amount of capital.

- Five fictional equities update in price once per second.

- You can buy or sell any equity in any quantity.

- Long and short positions are both supported.

- Displayed cash represents total account value (net liquidation value).

- Score is defined as current account value minus starting capital.

- If account value drops below zero, the simulation ends and can be restarted.

- There is no backend, no external data source, and no persistence between runs.

### Equities

The simulator includes five made-up companies:

- NL Co

- Bank of Finance

- DCF Industries

- Walls and Streets Architecture

- AI Tech

Each equity has its own price dynamics and starting price range. Initial prices are randomized at the beginning of each run.

### Price Model

Prices are generated using Geometric Brownian Motion (GBM), a commonly used stochastic process in quantitative finance.

Each second, prices evolve according to:

`S(t + Δt) = S(t) × exp((μ − 0.5σ²)Δt + σ√Δt · Z)`


Where:

- S(t) is the current price

- μ (mu) is the drift term, representing expected return

- σ (sigma) is the volatility term

- Δt is the time step (one second)

- Z is a random shock drawn from a normal distribution

Each equity is assigned its own drift and volatility parameters, resulting in different price behaviors across assets. The stochastic component introduces randomness while the drift term allows for directional movement over time.

I.E Each stock behaves differently because some have more volatility, some trend more strongly, and even though prices move randomly from moment to moment, there is an underlying tendency that shapes where they go over time.

Prices are constrained to remain positive, and recent price history is retained for charting purposes.

### Trading and Portfolio Accounting

Trades are executed at the current simulated market price.

Internally, the simulator tracks:

- A cash balance

- A position quantity for each equity (positive for long, negative for short)

- Total account value (displayed as cash) is calculated as:

- cash_balance + Σ(position_quantity × current_price)


Short positions reduce account value as prices rise and increase account value as prices fall, consistent with standard portfolio accounting.

### Interface

The UI displays:

A real-time price chart for the selected equity

A chart of total account value over time

A live portfolio list showing open positions and quantities

Charts update once per second and reflect all price and trade changes immediately.

## Project Structure

- index.html   // Application layout and structure
- styles.css   // Styling and layout
- app.py       // Simulation and trading logic
- README.md

## License

This project is licensed under the GNU GPL v3.0. See the LICENSE file for details.

## Author

Nick Lukas