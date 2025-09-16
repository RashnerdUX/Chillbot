### Sample Response for using the Jupiter Quote API to assess liquidity of token

{
  "inputMint": "So1111...",          # What you are swapping IN (SOL here)
  "inAmount": "100000000",           # Amount of input tokens (lamports)
  "outputMint": "V5cCiSi...pump",    # What you are swapping INTO (the meme token)
  "outAmount": "664465560",          # Expected output amount (raw, before decimals)
  "otherAmountThreshold": "661143233", # Minimum amount after slippage tolerance
  "slippageBps": 50,                 # Slippage tolerance = 0.5% (50 basis points)
  "priceImpactPct": "0",             # Estimated price impact on the pool
  "routePlan": [
    {
      "swapInfo": {
        "ammKey": "9eyegrQ...",      # Address of the AMM pool being used
        "label": "Pump.fun Amm",     # Which AMM (Raydium / Orca / Pump.fun, etc.)
        "inAmount": "100000000",     # Input into this swap step
        "outAmount": "664465560",    # Output from this swap step
        "feeAmount": "300000",       # Trading fee in lamports
        "feeMint": "So1111..."       # Mint of fee currency (SOL in this case)
      },
      "percent": 100,                 # % of your trade going through this route
      "bps": 10000                    # Allocation (10000 = 100%)
    }
  ],
  "swapUsdValue": "23.5840...",      # Approx USD value of your input trade
  "mostReliableAmmsQuoteReport": {
    "info": {
      "9eyegrQ...": "664465560",     # Main AMM used with expected output
      "Czfq3x...": "23582644"        # Backup AMM considered
    }
  },
  "contextSlot": 366978396,          # Solana slot when this quote was taken
  "timeTaken": 0.0035                # API latency in seconds
}