
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

        # Add target allocations to portfolio data for the table
        portfolio['target_allocations'] = self.allocations

        # Print enhanced market overview table with portfolio data
        self.price_fetcher.print_price_table(portfolio)

        # Get remaining price data
        price_summary = self.price_fetcher.get_price_summary()
        btc_dominance = self.coingecko.get_btc_dominance()

        if not all([price_summary, btc_dominance]):
            return "Error: Could not fetch required data"

        # Calculate opportunities for each token
        opportunities = {}
        for token in self.allocations.keys():
            target_allocation = self.allocations[token] * 100
            current_allocation = portfolio['holdings'][token]['percentage']
            allocation_difference = target_allocation - current_allocation

            weighted_change = (
                0.7 * price_summary[token][TimeFrame.DAYS_7] +
                0.3 * price_summary[token][TimeFrame.HOURS_24]
            )

            score = weighted_change - (allocation_difference * 2)

            opportunities[token] = {
                'weighted_change': weighted_change,
                'price': price_summary[token][TimeFrame.CURRENT],
                'changes': {
                    '24h': price_summary[token][TimeFrame.HOURS_24],
                    '7d': price_summary[token][TimeFrame.DAYS_7]
                },
                'allocation_difference': allocation_difference,
                'score': score
            }

        # Find best opportunity
        best_token = min(opportunities.items(), key=lambda x: x[1]['score'])[0]
        if opportunities[best_token]['allocation_difference'] <= 0:
            return None

        return {
            'token': best_token,
            'amount_usd': self.daily_budget,
            'reasoning': {
                'price': opportunities[best_token]['price'],
                '24h_change': opportunities[best_token]['changes']['24h'],
                '7d_change': opportunities[best_token]['changes']['7d'],
                'weighted_change': opportunities[best_token]['weighted_change'],
                'allocation_difference': opportunities[best_token]['allocation_difference'],
                'btc_dominance': btc_dominance
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
