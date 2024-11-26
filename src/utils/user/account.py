from time import time
from asyncio import sleep

from web3.exceptions import TransactionNotFound
from web3.types import TxParams
from web3.eth import AsyncEth
from eth_typing import HexStr
from web3 import AsyncWeb3
from loguru import logger

from config import BASE_RPC


class Account:
    def __init__(
            self,
            private_key: str,
            rpc=BASE_RPC,
            *,
            proxy: str | None = None
    ) -> None:
        self.private_key = private_key

        request_args = {} if proxy is None else {
            'proxy': proxy
        }

        self.web3 = AsyncWeb3(
            provider=AsyncWeb3.AsyncHTTPProvider(
                endpoint_uri=rpc,
                request_kwargs=request_args
            ),
            modules={'eth': (AsyncEth,)},
        )
        self.account = self.web3.eth.account.from_key(private_key)
        self.wallet_address = self.account.address

    async def sign_transaction(self, tx: TxParams) -> HexStr:
        signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
        raw_tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash = self.web3.to_hex(raw_tx_hash)
        return tx_hash

    async def wait_until_tx_finished(self, tx_hash: HexStr, max_wait_time=180) -> bool:
        start_time = time()
        while True:
            try:
                receipts = await self.web3.eth.get_transaction_receipt(tx_hash)
                status = receipts.get("status")
                if status == 1:
                    logger.success(f"Transaction confirmed!")
                    return True
                elif status is None:
                    await sleep(0.3)
                else:
                    logger.error(f"Transaction failed!")
                    return False
            except TransactionNotFound:
                if time() - start_time > max_wait_time:
                    print(f'FAILED TX: {tx_hash}')
                    return False
                await sleep(1)
