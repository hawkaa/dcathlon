
import logging
import json
import yaml
from pathlib import Path
from colorama import Fore, Style, init
from .price_fetcher import PriceFetcher, TimeFrame
from .coingecko import CoinGeckoAPI

# Initialize colorama
init()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crypto_dca.log')
    ]
)

class DCATrader:
    def __init__(self, config_path='config.yaml'):
        # Load configuration
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found. Please copy config.yaml.example to {config_path} and update values."
            )

        with open(config_file) as f:
            config = yaml.safe_load(f)

        # Load configuration sections
        self.allocations = config['allocations']
        self.trading_portfolio = config['trading_portfolio']
        self.long_term_portfolio = config['long_term_portfolio']

        # Combine portfolios for total holdings
        self.portfolio = {
            token: self.trading_portfolio.get(token, 0) + self.long_term_portfolio.get(token, 0)
            for token in self.allocations.keys()
        }

        # Load settings
        self.daily_budget = config['settings']['daily_budget']
        self.min_trade_size = config['settings']['min_trade_size']

        # Initialize APIs and price fetcher
        self.coingecko = CoinGeckoAPI()
        self.price_fetcher = PriceFetcher(list(self.allocations.keys()))

        logging.info(f"Initialized DCA Trader with ${self.daily_budget} daily budget")
        logging.info(f"Target allocations: {json.dumps(self.allocations, indent=2)}")

    def analyze_portfolio(self):
        """Analyze current portfolio holdings and distribution"""
        price_summary = self.price_fetcher.get_price_summary()
        if not price_summary:
            logging.error("Could not analyze portfolio - price fetch failed")
            return None

        # Calculate holdings values and total portfolio value
        holdings = {}
        total_value = 0

        for token, amount in self.portfolio.items():
            current_price = price_summary[token][TimeFrame.CURRENT]
            value = amount * current_price
            holdings[token] = {
                'amount': amount,
                'price': current_price,
                'value_usd': value,
            }
            total_value += value

        # Calculate percentages
        for token in holdings:
            holdings[token]['percentage'] = (holdings[token]['value_usd'] / total_value) * 100

        # Sort holdings by value
        sorted_holdings = dict(sorted(holdings.items(),
                                    key=lambda x: x[1]['value_usd'],
                                    reverse=True))

        return {
            'total_value': total_value,
            'holdings': sorted_holdings
        }

    def get_trade_recommendation(self):
        """Generate trade recommendation based on portfolio analysis"""
        logging.info("\n" + "="*50)
        logging.info("Starting new trade analysis...")

        # Get portfolio analysis first
        portfolio = self.analyze_portfolio()
        if not portfolio:
            return "Error: Could not analyze portfolio"

        portfolio['target_allocations'] = self.allocations

        price_summary = self.price_fetcher.get_price_summary()
        if not price_summary:
            return "Error: Could not fetch required data"

        # Calculate opportunities for each token
        opportunities = {}
        for token in self.allocations.keys():
            target_allocation = self.allocations[token] * 100
            current_allocation = portfolio['holdings'][token]['percentage']
            allocation_diff_pct = target_allocation - current_allocation
            print()

            # Weight composition:
            # - 50% 7-day performance
            # - 25% 24h performance
            # - 25% allocation difference
            score = (
                0.50 * price_summary[token][TimeFrame.DAYS_7] +    # 7d performance (50%)
                0.25 * price_summary[token][TimeFrame.HOURS_24] +  # 24h performance (25%)
                0.25 * allocation_diff_pct                         # allocation diff (25%)
            )


            opportunities[token] = {
                'price': price_summary[token][TimeFrame.CURRENT],
                'changes': {
                    '24h': price_summary[token][TimeFrame.HOURS_24],
                    '7d': price_summary[token][TimeFrame.DAYS_7]
                },
                'allocation_diff_pct': allocation_diff_pct,
                'score': score
            }

        # Add scores to portfolio data for table display
        portfolio['scores'] = {token: data['score'] for token, data in opportunities.items()}

        # Now print the table with scores included
        self.price_fetcher.print_price_table(portfolio)

        # Filter out over-allocated tokens
        under_allocated = {
            token: data for token, data in opportunities.items()
            if data['allocation_diff_pct'] > 0
        }

        if not under_allocated:
            return None

        # Find best opportunity among under-allocated tokens
        best_token = min(under_allocated.items(), key=lambda x: x[1]['score'])[0]

        return {
            'token': best_token,
            'amount_usd': self.daily_budget,
            'reasoning': {
                'price': opportunities[best_token]['price'],
                '24h_change': opportunities[best_token]['changes']['24h'],
                '7d_change': opportunities[best_token]['changes']['7d'],
                'score': opportunities[best_token]['score'],
                'allocation_difference': opportunities[best_token]['allocation_diff_pct'],
            },
            'portfolio': portfolio
        }

def main():
    trader = DCATrader()
    portfolio_analysis = trader.analyze_portfolio()
    recommendation = trader.get_trade_recommendation()

    if recommendation:
        logging.info("\n=== TRADE RECOMMENDATION ===")
        logging.info(f"Buy {recommendation['token'].upper()}")
        logging.info(f"Amount: ${recommendation['amount_usd']:.2f}")
        logging.info(f"Current price: ${recommendation['reasoning']['price']:.4f}")
        logging.info(f"24h change: {recommendation['reasoning']['24h_change']:.1f}%")
        logging.info(f"7d change: {recommendation['reasoning']['7d_change']:.1f}%")
    else:
        logging.info("\nNo trade recommended at this time")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("\nGracefully shutting down...")
