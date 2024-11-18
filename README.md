# DCAthlon 🏃‍♂️

Your personal crypto portfolio DCA trainer. Analyze your holdings, track target allocations, and get recommendations for your next investment move.

## Features

- Real-time price tracking via CoinGecko API
- Portfolio analysis with target allocation tracking
- Price trend analysis (24h and 7d changes)
- Beautiful console output with colored indicators

## Installation

```bash
git clone https://github.com/hawkaa/dcathlon.git
cd dcathlon
rye sync
```

## Configuration

Copy `config.yaml.example` to `config.yaml` and configure your:
- Trading portfolio (exchange holdings)
- Long term portfolio (cold storage)
- Target allocations
- DCA settings

## Usage

```bash
python run.py
```

## Credits

- Market data: [CoinGecko API](https://www.coingecko.com/en/api)
- Initial implementation: Håkon Åmdal
- AI assistance: Claude (Anthropic)

## License

MIT

## Disclaimer

For informational purposes only. Not financial advice.
