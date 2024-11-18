from enum import Enum
from typing import Dict, Optional
import logging
import requests
import pandas as pd
from tabulate import tabulate
import time
from .coingecko import CoinGeckoAPI

class TimeFrame(Enum):
    CURRENT = "current"
    HOURS_24 = "24h"
    DAYS_7 = "7d"

class PriceFetcher:
    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.price_cache: Dict[str, float] = {}
        self.history_cache: Dict[str, pd.DataFrame] = {}
        self.api = CoinGeckoAPI()

    def get_price_summary(self) -> Dict[str, Dict[TimeFrame, float]]:
        """Get summary of prices and changes for all tokens"""
        summary = {}
        histories = self.get_price_histories()

        for token in self.tokens:
            if token not in histories:
                continue

            history = histories[token]
            current_price = history['price'].iloc[-1]
            day_ago_price = history['price'].iloc[-24]
            week_ago_price = history['price'].iloc[0]

            summary[token] = {
                TimeFrame.CURRENT: current_price,
                TimeFrame.HOURS_24: ((current_price - day_ago_price) / day_ago_price) * 100,
                TimeFrame.DAYS_7: ((current_price - week_ago_price) / week_ago_price) * 100
            }

        return summary

    def get_price_histories(self) -> Dict[str, pd.DataFrame]:
        """Get 7-day price histories for all tokens"""
        if not self.history_cache:
            for token in self.tokens:
                history = self.api.get_price_history(token)
                if history is not None:
                    self.history_cache[token] = history
        return self.history_cache

    def print_price_table(self, portfolio_data: Optional[dict] = None):
        """Print formatted table of current prices and changes"""
        summary = self.get_price_summary()

        table_data = []
        headers = ["Token", "Price", "24h Change", "7d Change", "Holdings", "Value USD", "Current %", "Target %", "Diff"]

        for token, prices in summary.items():
            row = [
                token.upper(),
                f"${prices[TimeFrame.CURRENT]:,.2f}",
                f"{prices[TimeFrame.HOURS_24]:+.2f}%",
                f"{prices[TimeFrame.DAYS_7]:+.2f}%",
            ]

            if portfolio_data and token in portfolio_data['holdings']:
                holding = portfolio_data['holdings'][token]
                target_pct = portfolio_data['target_allocations'][token] * 100
                current_pct = holding['percentage']
                diff = current_pct - target_pct

                # Color the difference based on if we're under/over target
                diff_color = "\033[32m" if diff < 0 else "\033[31m"  # Green if under, red if over
                diff_str = f"{diff_color}{diff:+.1f}%\033[0m"

                row.extend([
                    f"{holding['amount']:.4f}",
                    f"${holding['value_usd']:,.2f}",
                    f"{current_pct:.1f}%",
                    f"{target_pct:.1f}%",
                    diff_str
                ])
            else:
                row.extend(["-", "-", "-", "-", "-"])

            table_data.append(row)

        print("\nPortfolio and Market Overview:")
        if portfolio_data:
            print(f"Total Portfolio Value: ${portfolio_data['total_value']:,.2f}")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
