# Algorithmic Trading Bot

A production-grade algorithmic trading system designed for robustness, reliability, and risk management. This system prioritizes survival and risk controls while implementing a phased approach to algorithmic trading.

## Features

- **Robust Data Pipeline**: Ingests data from multiple sources (Polygon.io, Binance) with built-in retry logic, rate limiting, and quality checks.
- **Time-Aware Feature Engineering**: Prevents lookahead bias in model training and inference.
- **Strategy Implementation**: Modular strategy architecture, including mean reversion and other algorithmic approaches.
- **Strict Risk Management**: position sizing, portfolio heat limits, drawdown protection, and daily loss limits.
- **Realistic Backtesting**: Accounts for commissions, slippage, and market impact.
- **Comprehensive Logging**: JSON-structured logging for production monitoring.

## Project Structure

```text
Trading Bot/
├── config/             # YAML configuration files for different environments
├── src/                # Source code
│   ├── data/           # Data ingestion, processing, and quality checks
│   ├── infrastructure/ # Shared utilities, logging, and retry logic
│   ├── models/         # Feature engineering and strategy logic
│   └── risk/           # Risk management and position sizing
├── tests/              # Comprehensive test suite
├── .env.example        # Template for environment variables
├── requirements.txt    # Python dependencies
└── main.py             # Entry point for the application
```

## Getting Started

### Prerequisites

- Python 3.9+
- [Git](https://git-scm.com/)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repository-url>
   cd "Trading Bot"
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

1. **Copy the environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`** and add your API keys:
   - `POLYGON_API_KEY`: Your Polygon.io API key.
   - `BINANCE_API_KEY`: Your Binance API key.
   - `BINANCE_SECRET_KEY`: Your Binance secret key.

3. **Environments**:
   The bot supports `dev` and `prod` environments via YAML files in the `config/` directory.

### Usage

Run the main application:
```bash
python main.py
```

### Testing

Run the test suite using `pytest`:
```bash
pytest
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
