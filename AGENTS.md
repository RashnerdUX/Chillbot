# Chillbot - Solana Meme Token Trading Bot

## Project Overview
Just a chill guy making you sweet cash - automated Solana meme token trading with risk management, honeypot detection, and real-time analytics.

## Dev Environment Setup
- Use Python 3.10+ with `uv` for dependency management
- Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Install Solana CLI: `sh -c "$(curl -sSfL https://release.solana.com/stable/install)"`
- Set up devnet: `solana config set --url devnet`
- Create test wallet: `solana-keygen new --outfile ~/.config/solana/devnet.json`
- Install dependencies: `uv sync`
- Lock dependencies for production: `uv pip compile pyproject.toml -o requirements.lock`
- Run commands with: `uv run <command>` (no need to activate venv)
- Use `solana balance` to check devnet SOL (airdrop with `solana airdrop 2`)

## Architecture & Modules
```
src/
├── core/
│   ├── wallet_manager.py     # Keypair handling, transaction signing
│   ├── rpc_client.py         # Solana RPC interactions
│   └── swap_executor.py      # Jupiter/Raydium swap logic
├── security/
│   ├── honeypot_detector.py  # Token safety checks
│   └── liquidity_checker.py  # Pool liquidity validation
├── monitoring/
│   ├── logger.py            # Structured logging
│   ├── metrics.py           # Performance tracking
│   └── discord_notifier.py  # Lightweight alert system
└── tests/
    ├── test_swaps.py        # Devnet swap testing
    └── mocks/               # Mock RPC responses
```

## Key Dependencies
- `solana-py>=0.30.0` - Solana blockchain interactions
- `jupiter-python-sdk` - DEX aggregator integration
- `httpx>=0.24.0` - Async HTTP client for RPC calls
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio` - Async test support

## Testing Instructions
- **Always test on devnet first**: Set `SOLANA_RPC_URL=https://api.devnet.solana.com`
- Run full test suite: `uv run pytest tests/ -v`
- Test specific swap functionality: `uv run pytest tests/test_swaps.py::test_jupiter_swap -s`
- **Mock RPC responses**: Use `tests/mocks/rpc_responses.json` containing:
  - Sample successful/failed swap transactions
  - Token metadata responses (name, symbol, decimals)
  - Jupiter route responses with price quotes
  - Honeypot detection API responses
  - Liquidity pool data from Raydium/Orca
- Integration tests require devnet SOL: `solana airdrop 2` before running
- Performance tests: `uv run pytest tests/test_performance.py --benchmark-only`
- Security tests: `uv run pytest tests/test_honeypot_detection.py -v`

## Security Guidelines
- **Never commit private keys** - Use environment variables or `.env` files (gitignored)
- **Validate all token addresses** - Check against known scam lists
- **Implement slippage protection** - Max 5% slippage for meme tokens
- **Rate limit RPC calls** - Respect provider limits (10 req/sec for public RPCs)
- **Use simulation before execution** - Always call `simulate_transaction()` first
- **Implement circuit breakers** - Stop trading after 3 consecutive failures

## Configuration
```python
# .env file (never commit)
SOLANA_RPC_URL=https://api.devnet.solana.com
WALLET_PRIVATE_KEY=your_base58_private_key
JUPITER_API_KEY=optional_for_rate_limits
MAX_SLIPPAGE=0.05
MAX_POSITION_SIZE_SOL=1.0
```

## Common Patterns
- **Async transaction handling**: All RPC calls should be async
- **Error handling**: Wrap RPC calls in try/except with specific Solana exceptions
- **Transaction confirmation**: Always wait for confirmation before proceeding
- **Logging**: Use structured JSON logging with transaction signatures
- **Retry logic**: Implement exponential backoff for failed RPC calls

## API Integration
- **Jupiter API**: Use for swap routing and price discovery
- **Birdeye API**: Token metadata and volume data
- **Solscan API**: Transaction history and wallet tracking
- **DexScreener**: Real-time price feeds and chart data

## Performance Requirements
- **Transaction speed**: <500ms from signal to submission
- **RPC latency**: Use dedicated RPC endpoints for production
- **Memory usage**: Keep token cache under 100MB
- **Error rate**: <1% transaction failures under normal conditions

## Deployment Guidelines
- **Devnet testing**: All features must pass devnet integration tests
- **Mainnet preparation**: Use `solana config set --url mainnet-beta`
- **Monitoring & Alerts**: 
  - Lightweight: Discord webhook for failed transactions (`src/monitoring/discord_notifier.py`)
  - Production: Prometheus metrics + Grafana dashboards
  - Log aggregation: Use structured JSON logging with transaction signatures
  - Health checks: HTTP endpoint at `/health` for uptime monitoring
- **Backup wallet**: Keep recovery phrase secure and separate
- **Gradual rollout**: Start with small position sizes on mainnet

## Code Style
- Follow PEP 8 with `ruff` formatting: `uv run ruff format src/ tests/`
- Linting with ruff: `uv run ruff check src/ tests/`
- Type hints required: Use `uv run mypy src/` to check
- Docstrings for public functions: Google style
- No hardcoded values: Use configuration files or environment variables
- Async/await patterns: Prefer async operations for all I/O

## Debugging
- Enable debug logging: Set `LOG_LEVEL=DEBUG` in environment
- Transaction tracing: Log all transaction signatures for investigation
- RPC debugging: Use `solana logs` to watch transaction execution
- Performance profiling: Use `pytest-benchmark` for bottleneck identification

## PR Guidelines
- Title format: `[module] brief description` (e.g., `[swap] add Jupiter integration`)
- Run linting before commit: `uv run ruff format src/ && uv run ruff check src/ && uv run mypy src/ && uv run pytest tests/`
- Include test coverage: New features require >80% test coverage
- Security review required for: wallet operations, RPC interactions, swap logic
- Performance benchmarks: Include before/after metrics for optimization PRs