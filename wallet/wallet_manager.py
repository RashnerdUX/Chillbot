from mnemonic import Mnemonic
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from spl.token.instructions import create_associated_token_account, transfer_checked, TransferCheckedParams
from solders.transaction import Transaction
from solana.rpc.types import TokenAccountOpts
from spl.token._layouts import ACCOUNT_LAYOUT
from solders.system_program import transfer, TransferParams
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
import base58

from models.wallet_models import SolanaToken

class WalletManager:
    def __init__(self):
        self.rpc_url = "https://api.mainnet-beta.solana.com"
        # For testing, I'll use a devnet URL and set the current wallet
        # TODO: Remember to remove the hardcoded values before deploying to production
        self.devnet_rpc_url = "https://api.devnet.solana.com"
        self.async_client = AsyncClient(self.devnet_rpc_url)
        # This is used to represent the wallet in the application
        self.wallet_name = "Gen_Wallet_from_Script"
        # This is the PubKey address of the wallet
        self.wallet_address = "76uuLyJ2VYFoMQPpiRoWyuJcvoNwCUPknPFvohbXDB1v"
        # This is the base58 encoded secret key of the wallet. This is the private key pair in string format
        self.user_wallet_secret = "b'\\x9ft\\xdbry\\x1d\\xa7F\\x1d\\xb2\\xd9\\x12\\xb1\\xa6ho\\xc9\\xb9[\\xad\\xa4\\xa8\\x9f5B:}\\xe7]c/r'"
        # This is the full keypair object, which includes both the public and private keys
        self.private_key = "4BuaxhsCd2QphjSKDqyM4rMwtw3ajhQ8K6vRrfDKmX4SxdtyMe1sH9Mo5G2dxLFrsgjpTiXeWsCqbwHNqNYxLi92"
        # This is the list of tokens associated with the wallet
        self.tokens: list[SolanaToken] = []


        # TODO: Implement secure password handling because this will be used to allow transactions from the wallet via the frontend
        self.user_password = "PythonRocks!"

    def create_wallet(self, wallet_name: str, password: str) -> dict:
        """
        Create a new wallet.

        Args:
            wallet_name (str): The name of the wallet.
            password (str): The password for the wallet.

        Returns:
            dict: The wallet information.
        """
        # Create a wallet
        keypair = Keypair()
        self.wallet_address = str(keypair.pubkey())
        self.user_wallet_secret = str(keypair.secret())
        self.wallet_name = wallet_name
        self.private_key = keypair

        # Set the user password
        self.user_password = password
        return {"address": self.wallet_address, "secret_key": self.user_wallet_secret, "private_key": self.private_key}
    
    def create_wallet_with_mnemonic(self, wallet_name: str, password:str) -> dict:
        """
        Create a new wallet with a mnemonic phrase.

        Args:
            wallet_name (str): The name of the wallet.
            password (str): The password for the wallet.

        Returns:
            dict: The wallet information.
        """
        mnemo = Mnemonic("english")
        # Use 256 bits if we want a 24-word mnemonic phrase
        mnemonic_phrase = mnemo.generate(strength=128)

        # Next is to derive the seed from the mnemonic phrase
        seed = mnemo.to_seed(mnemonic_phrase, passphrase="")

        # After deriving the seed, we can create a keypair from the seed
        private_key_bytes = seed[:32]  # Use the first 32 bytes of the seed
        keypair = Keypair.from_seed(private_key_bytes)

        # Store the wallet details
        self.wallet_name = wallet_name
        self.user_password = password
        self.wallet_address = str(keypair.pubkey())
        self.user_wallet_secret = str(keypair.secret())
        self.private_key = keypair

        return {"address": self.wallet_address, "mnemonic_phrase": mnemonic_phrase, "secret_key": self.user_wallet_secret, "private_key": self.private_key}

    def load_wallet_from_private_key(self, wallet_name: str, private_key: str, password: str) -> dict:
        """
        Load a wallet from a private key.

        Args:
            wallet_name (str): The name of the wallet.
            private_key (str): The private key of the wallet.
            password (str): The password for the wallet.

        Returns:
            dict: The wallet information.
        """
        # Load an existing wallet
        private_key_base58 = base58.b58decode(private_key)
        keypair = Keypair.from_bytes(private_key_base58)
        self.wallet_address = str(keypair.pubkey())
        self.user_wallet_secret = private_key
        self.wallet_name = wallet_name

        # Set the user password
        self.user_password = password

        # Since we are loading an existing wallet, we do not return the secret key
        return {"address": self.wallet_address}
    
    def load_wallet_from_mnemonics(self, wallet_name: str, mnemonics: str, password: str) -> dict:
        """Load a wallet from a mnemonic phrase.

        Args:
            wallet_name (str): The name of the wallet.
            mnemonics (str): The mnemonic phrase.
            password (str): The password for the wallet.

        Returns:
            dict: The wallet information.
        """
        mnemo = Mnemonic("english")

        seed = mnemo.to_seed(mnemonics, passphrase="")
        private_key_bytes = seed[:32]  # Use the first 32 bytes of the seed
        keypair = Keypair.from_seed(private_key_bytes)

        self.wallet_address = str(keypair.pubkey())
        self.user_wallet_secret = str(keypair.secret())
        self.wallet_name = wallet_name

        # Set the user password
        self.user_password = password

        return {"address": self.wallet_address, "secret_key": self.user_wallet_secret}

    async def get_balance(self) -> float:
        """Get the balance of the wallet."""
        account_pubkey = Pubkey.from_string(self.wallet_address)

        async with self.async_client as client:
            # Get account balance
            balance = await client.get_balance(account_pubkey)

            print(f"Account: {account_pubkey}")
            print(f"Balance: {balance.value} lamports")
            print(f"Balance: {balance.value / 1_000_000_000} SOL")
        return {"account_balance": balance.value / 1_000_000_000}
    
    async def get_wallet_token(self) -> float:
        owner = Pubkey.from_string(self.wallet_address)

        async with self.async_client as client:
            # Get token accounts by owner
            token_accounts = await client.get_token_accounts_by_owner(
                owner,
                TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
            )

            print(f"Owner: {owner}")
            print(f"Found {len(token_accounts.value)} token accounts:\n")
            
            for token_account in token_accounts.value:
                token_data = ACCOUNT_LAYOUT.parse(token_account.account.data)
                mint_base58 = base58.b58encode(token_data.mint).decode('utf-8')
                print(f"Pubkey: {token_account.pubkey}")
                print(f"Owner: {token_account.account.owner}")
                print(f"Lamports: {token_account.account.lamports}")
                print(f"Mint: {token_data.mint}")
                print(f"Token Mint: {mint_base58}")
                print(f"Balance: {token_data.amount / 10**6}")
                print(f"Data Length: {len(token_account.account.data)} bytes")
                print("=" * 50)

                token = SolanaToken(
                    token_address=mint_base58,
                    token_balance=token_data.amount / 10**6,
                )
                self.tokens.append(token)

            """total_balance = 0
            for token_account in token_accounts.value:
                account_info = await client.get_token_account_balance(Pubkey.from_string(token_account.pubkey))
                total_balance += float(account_info.value.amount) / (10 ** account_info.value.decimals)

            print(f"Account: {account_pubkey}")
            print(f"Token Balance for wallet {self.wallet_name}: {total_balance}")"""
        return {"token_balance":"nothing for now"}
    
    async def get_token_balance(self) -> dict:
        """Get the token balance of the wallet."""
        await self.get_balance()
        await self.get_wallet_token()
        return {"account_balance": await self.get_balance(), "tokens": self.tokens}
    
    async def send_sol(self, recipient_address: str, amount: float) -> dict:
        """Send SOL to another wallet.

        Args:
            recipient_address (str): The recipient's wallet address.
            amount (float): The amount of SOL to send in lamports. Note: 1 SOL = 1_000_000_000 lamports.

        Returns:
            dict: The transaction information.
        """
        async with self.async_client as client:
            LAMPORTS_PER_SOL = 1_000_000_000
            # Get latest blockhash
            latest_blockhash = await client.get_latest_blockhash()

            # Create transfer instruction
            transfer_instruction = transfer(
                TransferParams(
                    from_pubkey=Pubkey.from_string(self.wallet_address),
                    to_pubkey=Pubkey.from_string(recipient_address),
                    lamports=amount, #The amount is in lamports (1 SOL = 1_000_000_000 lamports)
                )
            )

            # Create message
            message = MessageV0.try_compile(
                payer=Pubkey.from_string(self.wallet_address),
                instructions=[transfer_instruction],
                address_lookup_table_accounts=[],
                recent_blockhash=latest_blockhash.value.blockhash
            )

            # Create transaction
            transaction = VersionedTransaction(message, [Keypair.from_base58_string(self.private_key)])

            print(f"Sender: {self.wallet_address}")
            print(f"Recipient: {recipient_address}")
            print(f"Transfer Amount: {amount / LAMPORTS_PER_SOL} SOL")
            print(f"Transaction created successfully")

            return {"status": "success", "transaction": transaction}

    async def send_token(self, recipient_address: str, token_address: str, amount: float, decimals: int = 6) -> dict:
        # For sender, the keypair is needed to sign the transaction
        sender = Keypair.from_base58_string(self.private_key)
        # For recipient, only the public key is needed
        recipient = Pubkey.from_string(recipient_address)

        # Example token mint (USDC devnet)
        token_mint = Pubkey.from_string(token_address)

        async with self.async_client as rpc:
            # Get or create associated token accounts for sender and recipient
            sender_token_account = await self.get_or_create_ata(owner_pubkey=sender.pubkey(), mint=token_mint, payer=sender)
            recipient_token_account = await self.get_or_create_ata(owner_pubkey=recipient, mint=token_mint, payer=sender)
            # Get latest blockhash
            latest_blockhash = await rpc.get_latest_blockhash()

            # Create transfer instruction
            transfer_instruction = transfer_checked(
                TransferCheckedParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=sender_token_account,
                    mint=token_mint,
                    dest=recipient_token_account,
                    owner=sender.pubkey(),
                    amount=amount,
                    decimals=decimals
                )
            )

            # Create message
            message = MessageV0.try_compile(
                payer=sender.pubkey(),
                instructions=[transfer_instruction],
                address_lookup_table_accounts=[],
                recent_blockhash=latest_blockhash.value.blockhash
            )

            # Create transaction
            transaction = VersionedTransaction(message, [sender])

            print(f"Sender: {sender.pubkey()}")
            print(f"Recipient: {recipient.pubkey()}")
            print(f"Token Mint: {token_mint}")
            print(f"Transfer Amount: {amount / (10 ** decimals)} tokens")
            print(f"Transaction created successfully")

    async def get_or_create_ata(self, owner_pubkey, mint, payer):
        """Get or create the Associated Token Account for an owner and mint."""
        ata = Pubkey.find_program_address(
            [bytes(owner_pubkey), bytes(TOKEN_PROGRAM_ID), bytes(mint)],
            ASSOCIATED_TOKEN_PROGRAM_ID
        )[0]
        
        # Check if ATA exists
        response = await self.async_client.get_token_accounts_by_owner(
            owner_pubkey,
            TokenAccountOpts(program_id=TOKEN_PROGRAM_ID, mint=mint)
        )
        for account in response.value:
            if str(account.pubkey) == str(ata):
                return ata
        
        # Create ATA if it doesn't exist
        instruction = create_associated_token_account(
            payer= payer.pubkey(),
            owner=owner_pubkey,
            mint=mint
        )
        latest_blockhash = await self.async_client.get_latest_blockhash()
        tx = Transaction().add(instruction)
        tx.recent_blockhash = latest_blockhash.value.blockhash
        tx.sign(payer)
        await self.async_client.send_transaction(tx)
        return ata

if __name__ == "__main__":

    import os
    from dotenv import load_dotenv
    import asyncio

    load_dotenv()
    dUSDC_mint_address = "USDCoctVLVnvTXBEuP9s8hntucdJokbo17RwHuNXemT"
    chillbot_mint_address = "3JutSRiMmvnMUSJrvbmpNuFvuLbQ6iGCQg8Ps5YAaahB"
    my_bonk_address = "4B1FiyECpqgsiy6vdtyu292Q7NuFhFtFx1PC1rakgHzc"
    wm = WalletManager()
    wallet_info = asyncio.run(wm.send_token(
        recipient_address=my_bonk_address,
        token_address=dUSDC_mint_address,
        amount=10_000_000,
        decimals=6
    ))
    print(wallet_info)

    """ private_key = os.getenv("WALLET_PRIVATE_KEY")
    base58_key = base58.b58decode(private_key)
    print(f"base58_key: {base58_key}")"""