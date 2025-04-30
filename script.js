// Initialize TradingView widget
// Replace your initTradingViewChart function with:
function initTradingViewChart(symbol, marketType, interval) {
    const container = document.getElementById('tradingview_chart');
    if (!container) return;
    
    // Clear previous chart
    container.innerHTML = '';
    
    // Convert your timeframe to TradingView's format
    const tvInterval = convertToTradingViewInterval(interval);
    
    // Format symbol correctly
    const tvSymbol = `BINANCE:${symbol}${marketType === 'futures' ? '.P' : ''}`;
    
    new TradingView.widget({
        "autosize": true,
        "symbol": tvSymbol,
        "interval": tvInterval,
        "timezone": "Etc/UTC",
        "theme": "light",
        "style": "1",
        "locale": "en",
        "container_id": "tradingview_chart",
        "height": "100%",
        "width": "100%"
    });
}

// Add this helper function (put it right above initTradingViewChart)
function convertToTradingViewInterval(yourInterval) {
    const mapping = {
        '1m': '1',
        '3m': '3',
        '5m': '5',
        '15m': '15',
        '30m': '30',
        '1h': '60',
        '2h': '120',
        '4h': '240',
        '6h': '360',
        '8h': '480',
        '12h': '720',
        '1d': 'D',
        '3d': '3D',
        '1w': 'W',
        '1M': 'M'
    };
    return mapping[yourInterval] || '60'; // Default to 1h if unknown
}
// DOM Elements
const analysisForm = document.getElementById('analysisForm');
const inputCheatsheetSection = document.getElementById('inputCheatsheetSection');
const resultsSection = document.getElementById('resultsSection');
const consoleOutput = document.getElementById('consoleOutput');
const backButton = document.getElementById('backButton');
const errorMessage = document.getElementById('errorMessage');
const cheatsheetContent = document.getElementById('cheatsheetContent');

// Cheat sheet data
const cheatSheetData = `
<h3>📈 Trading Indicator Rules</h3>
<ul>
    <li><strong>ADX TREND STRENGTH</strong><br>
        🟢 LONG: When trend is STRONG (ADX > 25) and +DI > -DI<br>
        🔴 SHORT: When trend is STRONG but -DI > +DI
    </li>
    <li><strong>EMA Cross</strong><br>
        🟢 LONG: Golden Cross (EMA50 > EMA200)<br>
        🔴 SHORT: Death Cross (EMA50 < EMA200)
    </li>
    <li><strong>Money Flow</strong><br>
        🟢 LONG: Negative flow (smart money leaving)<br>
        🔴 SHORT: Positive flow (money flooding in)
    </li>
    <li><strong>Market Mood</strong><br>
        🟢 LONG: Extreme FEAR (oversold)<br>
        🔴 SHORT: Extreme GREED (overbought)
    </li>
    <li><strong>Miners' Move</strong><br>
        🟢 LONG: Miners holding<br>
        🔴 SHORT: Miners dumping
    </li>
    <li><strong>MACD</strong><br>
        🟢 LONG: MACD line crosses ABOVE Signal<br>
        🔴 SHORT: MACD line crosses BELOW Signal
    </li>
    <li><strong>Volume Zones</strong><br>
        🟢 LONG: Near high volume support<br>
        🟠 SHORT: In weak resistance territory
    </li>
    <li><strong>RSI</strong><br>
        🟢 LONG: RSI < 30 (oversold)<br>
        🔴 SHORT: RSI > 70 (overbought)
    </li>
    <li><strong>Smart Money</strong><br>
        🟢 LONG: Big players buying<br>
        🔴 SHORT: Whales selling
    </li>
    <li><strong>Whale Watching</strong><br>
        🟢 LONG: Whale buys > 1.5× sells<br>
        🔴 SHORT: Whale sells > 1.5× buys
    </li>
    <li><strong>Stoch RSI</strong><br>
        🟢 LONG: StochRSI < 20<br>
        🔴 SHORT: StochRSI > 80
    </li>
    <li><strong>Support/Resistance</strong><br>
        🟢 LONG: Near support<br>
        🔴 SHORT: Near resistance
    </li>
</ul>

<h3>💡 Confidence Levels</h3>
<ul>
    <li>9+ indicators: Extreme Confidence 🚀🚀🚀</li>
    <li>7-9 indicators: High Confidence 🚀🚀</li>
    <li>6 indicators: Solid 🚀</li>
    <li>4-6 indicators: Caution ⚠️</li>
    <li>Below 4: Confirm LOSS 🛑</li>
</ul>
`;

// Load cheat sheet on page load
document.addEventListener('DOMContentLoaded', function() {
    if (cheatsheetContent) {
        cheatsheetContent.innerHTML = cheatSheetData;
    }
});

// Form submission
analysisForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Clear any previous errors
    errorMessage.textContent = '';
    errorMessage.classList.remove('show');

    // Show loading state
    const submitButton = this.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = 'Loading...';
    
    // Get form values
    const coinPair = document.getElementById('coinName').value.toUpperCase();
    const marketType = document.getElementById('marketType').value;
    const positionType = document.getElementById('positionType').value;
    const timeframe = document.getElementById('timeframe').value;
    
    if (!coinPair) {
        errorMessage.textContent = 'Please enter a coin pair (e.g., BTCUSDT)';
        errorMessage.classList.add('show');
        submitButton.disabled = false;
        submitButton.textContent = 'Analyze';
        return;
    }
    
    try {
        // Split timeframe for backend compatibility
        const timeValue = timeframe.slice(0, -1);
        const timeUnit = timeframe.slice(-1) === 'm' ? 'minutes' : 
                        timeframe.slice(-1) === 'h' ? 'hours' : 'days';
        
        const response = await fetch('http://localhost:5000/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                market_type: marketType,
                symbol: coinPair,
                trade_type: positionType,
                time_unit: timeUnit,
                time_value: timeValue
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.error || 'Analysis failed');
        
        // Update UI
        consoleOutput.textContent = data.console_output;
        if (data.structured_data) {
            // You can access data.structured_data.targets here if needed
            console.log('Price targets:', data.structured_data.targets);
        }
        if (inputCheatsheetSection) inputCheatsheetSection.style.display = 'none';
        if (resultsSection) resultsSection.style.display = 'grid';
        
        // Initialize chart with the same timeframe
        initTradingViewChart(coinPair, marketType, timeframe);
        
    } catch (error) {
        errorMessage.textContent = error.message.includes('out-of-bounds') 
            ? 'Invalid coin pair. Please check the symbol and try again.' 
            : error.message;
        errorMessage.classList.add('show');
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Analyze';
    }
});

// Back button functionality
backButton.addEventListener('click', function() {
    if (resultsSection) {
        resultsSection.style.display = 'none';
        resultsSection.classList.remove('active');
    }
    if (inputCheatsheetSection) {
        inputCheatsheetSection.style.display = 'grid';
    }
    window.scrollTo(0, 0);
});