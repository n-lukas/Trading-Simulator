import random
import math
import asyncio
import json
from js import document, window
from pyodide.ffi import create_proxy

# Game Constants
STARTING_CASH = 10000
WIN_THRESHOLD = 100000
EQUITIES = [
    'NL Co',
    'Bank of Finance',
    'DCF Industries',
    'Walls and Streets Architecture',
    'AI Tech'
]

# Price simulation parameters per equity (drift, volatility)
EQUITY_PARAMS = {
    'NL Co': {'drift': 0.0001, 'volatility': 0.02, 'basePrice': 50},
    'Bank of Finance': {'drift': 0.00008, 'volatility': 0.015, 'basePrice': 75},
    'DCF Industries': {'drift': 0.00012, 'volatility': 0.025, 'basePrice': 100},
    'Walls and Streets Architecture': {'drift': 0.00009, 'volatility': 0.018, 'basePrice': 60},
    'AI Tech': {'drift': 0.00015, 'volatility': 0.03, 'basePrice': 120}
}

# Game State
game_state = {
    'cashBalance': STARTING_CASH,
    'positions': {},
    'prices': {},
    'initialPrices': {},
    'averagePurchasePrices': {},
    'time': 0,
    'equityHistory': {},
    'cashHistory': [],
    'isRunning': False,
    'task': None
}

# DOM Elements
instructions_screen = document.getElementById('instructionsScreen')
trading_screen = document.getElementById('tradingScreen')
game_over_overlay = document.getElementById('gameOverOverlay')
win_overlay = document.getElementById('winOverlay')
start_button = document.getElementById('startButton')
try_again_button = document.getElementById('tryAgainButton')
play_again_button = document.getElementById('playAgainButton')
equity_select = document.getElementById('equitySelect')
quantity_input = document.getElementById('quantityInput')
quantity_up = document.getElementById('quantityUp')
quantity_down = document.getElementById('quantityDown')
buy_button = document.getElementById('buyButton')
sell_button = document.getElementById('sellButton')
cash_display = document.getElementById('cashDisplay')
score_display = document.getElementById('scoreDisplay')
portfolio_list = document.getElementById('portfolioList')
selected_equity_title = document.getElementById('selectedEquityTitle')

# Initialize positions
for equity in EQUITIES:
    game_state['positions'][equity] = 0
    game_state['equityHistory'][equity] = []
    game_state['averagePurchasePrices'][equity] = 0

def update_price(equity):
    """Geometric Brownian Motion price update"""
    params = EQUITY_PARAMS[equity]
    current_price = game_state['prices'][equity]
    dt = 1  # 1 second
    
    # Random shock (correlated across equities for realism)
    shock = (random.random() + random.random() + random.random() + random.random() - 2) / 2
    
    # GBM formula: S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
    drift_term = (params['drift'] - 0.5 * params['volatility'] * params['volatility']) * dt
    diffusion_term = params['volatility'] * math.sqrt(dt) * shock
    new_price = current_price * math.exp(drift_term + diffusion_term)
    
    # Ensure price doesn't go negative or too extreme
    game_state['prices'][equity] = max(0.01, new_price)
    
    # Store history (keep last 300 points)
    if equity not in game_state['equityHistory']:
        game_state['equityHistory'][equity] = []
    
    game_state['equityHistory'][equity].append({
        'time': game_state['time'],
        'price': game_state['prices'][equity]
    })
    
    if len(game_state['equityHistory'][equity]) > 300:
        game_state['equityHistory'][equity].pop(0)

def calculate_net_liquidation_value():
    """Calculate net liquidation value (displayed Total Equity)"""
    total_value = game_state['cashBalance']
    for equity in EQUITIES:
        total_value += game_state['positions'][equity] * game_state['prices'][equity]
    return total_value

def step_prices():
    """Update prices for all equities"""
    for equity in EQUITIES:
        update_price(equity)
    
    # Update cash history
    net_value = calculate_net_liquidation_value()
    game_state['cashHistory'].append({
        'time': game_state['time'],
        'value': net_value
    })
    
    # Keep last 300 points
    if len(game_state['cashHistory']) > 300:
        game_state['cashHistory'].pop(0)
    
    game_state['time'] += 1
    
    # Update UI
    update_ui()
    render_charts()
    
    # Check win condition
    if net_value >= WIN_THRESHOLD:
        win_game()
        return
    
    # Check game over condition
    if net_value <= 0:
        game_over()

def execute_trade(type):
    """Execute a trade"""
    equity = equity_select.value
    try:
        quantity = int(quantity_input.value)
    except (ValueError, TypeError):
        return
    
    if quantity < 1:
        return
    
    current_price = game_state['prices'][equity]
    trade_value = quantity * current_price
    
    if type == 'buy':
        current_position = game_state['positions'][equity]
        current_avg_price = game_state['averagePurchasePrices'].get(equity, 0)
        
        # Always allow buying back shorted stocks (negative positions)
        if current_position < 0:
            # Buying back a short position - calculate weighted average
            abs_current_qty = abs(current_position)
            if abs_current_qty > 0 and current_avg_price != 0:
                # Weighted average: (old_avg * old_qty + new_price * new_qty) / (old_qty + new_qty)
                new_qty = current_position + quantity  # This will be less negative or positive
                if new_qty <= 0:
                    # Still short, keep same average short price
                    game_state['averagePurchasePrices'][equity] = current_avg_price
                else:
                    # Covered the short and now long - new average is the purchase price
                    game_state['averagePurchasePrices'][equity] = current_price
            else:
                # First time buying this equity
                game_state['averagePurchasePrices'][equity] = current_price
            game_state['positions'][equity] += quantity
            game_state['cashBalance'] -= trade_value
        else:
            # Check margin limit: total absolute position value cannot exceed current portfolio value
            current_net_value = calculate_net_liquidation_value()
            
            # Calculate what the total position value would be after this trade
            total_new_position_value = 0
            for eq in EQUITIES:
                position_qty = game_state['positions'][eq]
                if eq == equity:
                    position_qty += quantity  # Add the new quantity for this equity
                total_new_position_value += abs(position_qty * game_state['prices'][eq])
            
            # Allow the trade only if total position value doesn't exceed portfolio value
            if total_new_position_value > current_net_value:
                window.alert('Cannot buy: Total position value cannot exceed your Total Equity. Sell some positions first.')
                return
            
            # Calculate weighted average purchase price
            if current_position == 0:
                # First purchase
                game_state['averagePurchasePrices'][equity] = current_price
            else:
                # Weighted average: (old_avg * old_qty + new_price * new_qty) / (old_qty + new_qty)
                total_cost = (current_avg_price * current_position) + (current_price * quantity)
                total_qty = current_position + quantity
                game_state['averagePurchasePrices'][equity] = total_cost / total_qty
            
            game_state['positions'][equity] += quantity
            game_state['cashBalance'] -= trade_value
    else:  # sell
        current_position = game_state['positions'][equity]
        
        # When selling, if going from long to short, reset average price
        if current_position > 0 and (current_position - quantity) < 0:
            # Going from long to short - new average is the sell price
            game_state['averagePurchasePrices'][equity] = current_price
        elif current_position < 0:
            # Increasing short position - calculate weighted average short price
            abs_current_qty = abs(current_position)
            current_avg_price = game_state['averagePurchasePrices'].get(equity, current_price)
            new_qty = abs(current_position - quantity)
            if abs_current_qty > 0 and current_avg_price != 0:
                total_cost = (current_avg_price * abs_current_qty) + (current_price * quantity)
                game_state['averagePurchasePrices'][equity] = total_cost / new_qty
            else:
                game_state['averagePurchasePrices'][equity] = current_price
        elif current_position == 0:
            # Creating a new short position - set average short sale price
            game_state['averagePurchasePrices'][equity] = current_price
        # If selling reduces long position but stays long, keep same average price (FIFO-like)
        
        game_state['positions'][equity] -= quantity
        game_state['cashBalance'] += trade_value
    
    update_ui()
    render_portfolio()

def update_ui():
    """Update UI elements"""
    net_value = calculate_net_liquidation_value()
    score = net_value - STARTING_CASH
    
    cash_display.textContent = f"${net_value:.2f}"
    score_display.textContent = f"${score:.2f}"
    
    # Color code score
    if score >= 0:
        score_display.style.color = '#27ae60'
    else:
        score_display.style.color = '#e74c3c'
    
    # Update portfolio to reflect live price changes
    render_portfolio()

def render_portfolio():
    """Render portfolio list"""
    portfolio_list.innerHTML = ''
    
    has_positions = any(game_state['positions'][equity] != 0 for equity in EQUITIES)
    
    if not has_positions:
        portfolio_list.innerHTML = '<p class="empty-portfolio">No positions yet</p>'
        return
    
    for equity in EQUITIES:
        qty = game_state['positions'][equity]
        if qty != 0:
            current_price = game_state['prices'][equity]
            position_value = qty * current_price
            # Use average price if set, otherwise fallback to current price
            avg_price = game_state['averagePurchasePrices'].get(equity, current_price)
            
            # Calculate gain/loss
            if qty > 0:
                # Long position: gain/loss = (current_price - avg_purchase_price) * quantity
                gain_loss = (current_price - avg_price) * qty
            else:
                # Short position: gain/loss = (avg_short_price - current_price) * abs(quantity)
                gain_loss = (avg_price - current_price) * abs(qty)
            
            item = document.createElement('div')
            item.className = 'portfolio-item'
            
            # Ticker/Name
            ticker = document.createElement('span')
            ticker.className = 'portfolio-ticker'
            ticker.textContent = equity
            
            # Quantity
            quantity_span = document.createElement('span')
            quantity_span.className = f"portfolio-quantity {'positive' if qty > 0 else 'negative'}"
            quantity_span.textContent = f"+{qty}" if qty > 0 else str(qty)
            
            # Value
            value_span = document.createElement('span')
            value_span.className = f"portfolio-value {'positive' if position_value >= 0 else 'negative'}"
            value_span.textContent = f"${abs(position_value):.2f}"
            
            # Gain/Loss
            gain_loss_span = document.createElement('span')
            gain_loss_span.className = f"portfolio-gainloss {'positive' if gain_loss >= 0 else 'negative'}"
            gain_loss_sign = '+' if gain_loss >= 0 else ''
            gain_loss_span.textContent = f"{gain_loss_sign}${gain_loss:.2f}"
            
            item.appendChild(ticker)
            item.appendChild(quantity_span)
            item.appendChild(value_span)
            item.appendChild(gain_loss_span)
            portfolio_list.appendChild(item)

def destroy_charts():
    """Destroy existing charts (JS-side)"""
    window.TradingCharts.destroy()

def init_charts():
    """Initialize charts (JS-side)"""
    window.TradingCharts.init()

def render_charts():
    """Update charts"""
    selected_equity = equity_select.value
    
    # Update equity chart
    payload = {'equity': {'labels': [], 'data': []}, 'cash': {'labels': [], 'data': []}}
    if selected_equity in game_state['equityHistory']:
        history = game_state['equityHistory'][selected_equity]
        if len(history) > 0:
            payload['equity']['labels'] = list(range(len(history)))
            payload['equity']['data'] = [d['price'] for d in history]
    
    # Update cash chart
    if len(game_state['cashHistory']) > 0:
        payload['cash']['labels'] = list(range(len(game_state['cashHistory'])))
        payload['cash']['data'] = [d['value'] for d in game_state['cashHistory']]

    # Send JSON only (no PyProxy objects) to JS
    window.TradingCharts.updateFromJson(json.dumps(payload))


async def _game_loop():
    while game_state['isRunning']:
        step_prices()
        await asyncio.sleep(1)

def update_selected_equity_chart():
    """Update selected equity chart title"""
    selected_equity = equity_select.value
    selected_equity_title.textContent = f"{selected_equity} Price"
    render_charts()

def start_game():
    """Start game"""
    global game_state
    
    # Reset state
    game_state['cashBalance'] = STARTING_CASH
    game_state['positions'] = {}
    game_state['prices'] = {}
    game_state['initialPrices'] = {}
    game_state['averagePurchasePrices'] = {}
    game_state['time'] = 0
    game_state['equityHistory'] = {}
    game_state['cashHistory'] = []
    game_state['isRunning'] = True
    
    for equity in EQUITIES:
        game_state['positions'][equity] = 0
        game_state['equityHistory'][equity] = []
        game_state['averagePurchasePrices'][equity] = 0
        
        # Randomize initial price within base range
        params = EQUITY_PARAMS[equity]
        variation = 0.2  # ±20% variation
        random_factor = 1 + (random.random() * 2 - 1) * variation
        game_state['initialPrices'][equity] = params['basePrice'] * random_factor
        game_state['prices'][equity] = game_state['initialPrices'][equity]
    
    # Initialize charts
    init_charts()
    
    # Show trading screen
    instructions_screen.classList.add('hidden')
    trading_screen.classList.remove('hidden')
    game_over_overlay.classList.add('hidden')
    win_overlay.classList.add('hidden')
    
    # Start price updates (Python asyncio loop; avoids JS callback proxies)
    if game_state.get('task') is not None:
        try:
            game_state['task'].cancel()
        except Exception:
            pass
    game_state['task'] = asyncio.create_task(_game_loop())
    
    # Initial UI update
    update_ui()
    render_portfolio()
    render_charts()

def game_over():
    """Game over"""
    game_state['isRunning'] = False
    if game_state.get('task') is not None:
        try:
            game_state['task'].cancel()
        except Exception:
            pass
        game_state['task'] = None
    game_over_overlay.classList.remove('hidden')

def win_game():
    """Win game"""
    game_state['isRunning'] = False
    if game_state.get('task') is not None:
        try:
            game_state['task'].cancel()
        except Exception:
            pass
        game_state['task'] = None
    win_overlay.classList.remove('hidden')

def reset_game():
    """Reset game"""
    game_state['isRunning'] = False
    if game_state.get('task') is not None:
        try:
            game_state['task'].cancel()
        except Exception:
            pass
        game_state['task'] = None
    
    # Destroy charts
    destroy_charts()
    
    # Reset to instructions screen
    instructions_screen.classList.remove('hidden')
    trading_screen.classList.add('hidden')
    game_over_overlay.classList.add('hidden')
    win_overlay.classList.add('hidden')
    
    # Reset quantity input
    quantity_input.value = 1

# Event Listeners
def on_start_click(event):
    start_game()

def on_try_again_click(event):
    reset_game()

def on_play_again_click(event):
    reset_game()

def on_quantity_up_click(event):
    try:
        current_value = int(quantity_input.value)
        quantity_input.value = max(1, current_value + 1)
    except (ValueError, TypeError):
        quantity_input.value = 1

def on_quantity_down_click(event):
    try:
        current_value = int(quantity_input.value)
        quantity_input.value = max(1, current_value - 1)
    except (ValueError, TypeError):
        quantity_input.value = 1

def on_buy_click(event):
    execute_trade('buy')

def on_sell_click(event):
    execute_trade('sell')

def on_equity_select_change(event):
    update_selected_equity_chart()

def on_quantity_input(event):
    try:
        value = int(event.target.value)
        if value < 1:
            event.target.value = 1
    except (ValueError, TypeError):
        event.target.value = 1

# IMPORTANT: keep JS proxies alive, otherwise Pyodide will destroy them and clicks won't work.
_event_proxies = []

def _bind_events():
    global _event_proxies
    _event_proxies = [
        create_proxy(on_start_click),
        create_proxy(on_try_again_click),
        create_proxy(on_play_again_click),
        create_proxy(on_quantity_up_click),
        create_proxy(on_quantity_down_click),
        create_proxy(on_buy_click),
        create_proxy(on_sell_click),
        create_proxy(on_equity_select_change),
        create_proxy(on_quantity_input),
    ]

    start_button.addEventListener('click', _event_proxies[0])
    try_again_button.addEventListener('click', _event_proxies[1])
    play_again_button.addEventListener('click', _event_proxies[2])
    quantity_up.addEventListener('click', _event_proxies[3])
    quantity_down.addEventListener('click', _event_proxies[4])
    buy_button.addEventListener('click', _event_proxies[5])
    sell_button.addEventListener('click', _event_proxies[6])
    equity_select.addEventListener('change', _event_proxies[7])
    quantity_input.addEventListener('input', _event_proxies[8])

_bind_events()

