from typing import Optional

from loguru import logger

from config import RETRIES, PAUSE_BETWEEN_RETRIES
from src.utils.common.wrappers.decorators import retry
from src.utils.proxy_manager import Proxy
from src.utils.request_client.client import RequestClient
from src.utils.user.account import Account


class SuperForm(Account, RequestClient):
    def __init__(
            self,
            private_key: str,
            proxy: Proxy | None
    ):
        Account.__init__(self, private_key=private_key, proxy=proxy.proxy_url if proxy else None)
        RequestClient.__init__(self, proxy=proxy)

    def __str__(self) -> str:
        return f'[{self.wallet_address}] | Claiming tokens...'

    @retry(retries=RETRIES, delay=PAUSE_BETWEEN_RETRIES, backoff=1.5)
    async def get_amount_of_tokens(self) -> float:
        response_json, status = await self.make_request(
            method='GET',
            url=f'https://www.superform.xyz/api/proxy/token-distribution/{self.wallet_address}/',
        )
        if status == 200:
            total_tokens = response_json['superrewards_stats']['total_tokens']
            return total_tokens
        return 0

    async def __get_tx_data(self) -> Optional[tuple[str, str]] | tuple[str, str]:
        response_json, response_status = await self.make_request(
            method='GET',
            url=f'https://www.superform.xyz/api/proxy/token-distribution/claim/{self.wallet_address}/',
        )
        if response_status != 200:

            if response_json['detail'] == 'user has already claimed':
                logger.warning(f'[{self.wallet_address}] | This wallet has already claimed tokens')
                return 'AlreadyClaimed', 'AlreadyClaimed'
        tx_data = response_json['transactionData']
        to_address = response_json['to']
        return tx_data, to_address

    @retry(retries=RETRIES, delay=PAUSE_BETWEEN_RETRIES, backoff=1.5)
    async def claim_tokens(self) -> Optional[bool]:
        tx_data, to_address = await self.__get_tx_data()
        if not tx_data:
            return

        if tx_data == 'AlreadyClaimed':
            return True

        tokens = await self.get_amount_of_tokens()

        tx = {
            'from': self.wallet_address,
            'value': 0,
            'to': self.web3.to_checksum_address(to_address),
            'nonce': await self.web3.eth.get_transaction_count(self.wallet_address),
            'chainId': await self.web3.eth.chain_id,
            'data': tx_data,
            'gasPrice': await self.web3.eth.gas_price
        }
        gas_limit = await self.web3.eth.estimate_gas(tx)
        tx.update({'gas': gas_limit})
        tx_hash = await self.sign_transaction(tx)
        confirmed = await self.wait_until_tx_finished(tx_hash)
        if confirmed:
            logger.success(
                f'[{self.wallet_address}] Successfully claimed {tokens} PIGGY tokens'
                f' | TX: https://basescan.org/tx/{tx_hash}'
            )
            return True
