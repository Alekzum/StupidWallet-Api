from dataclasses import dataclass
from typing import Union, Literal, Optional
import datetime
import asyncio
import httpx


@dataclass()
class ChequeMy:
    coin_id: int
    coin_amount: int
    password: str
    cheque_id: str
    comment: str
    
    @property
    def url(self):
        return f"https://t.me/stupidwallet_bot?start={self.cheque_id}"

    def __str__(self):
        return f"<Cheque {self.cheque_id} id{self.coin_id}*{self.coin_amount}>"

    def __repr__(self):
        return f"""{type(self).__name__}({dict([(name, getattr(self, name)) for name in dir(self) if name[0] != "_"])})"""


@dataclass
class Cheque(ChequeMy):
    status: bool
    coin_id: int
    coin_amount: int
    is_activated: bool
    has_password: bool
    comment: str
    cheque_id: str
    
    def __str__(self):
        return f"<Cheque {self.cheque_id} is_activated={self.is_activated} id{self.coin_id}*{self.coin_amount}>"

    def add_hash(self, hash: str):
        self.cheque_id = hash

@dataclass
class ChequeClaimed:
    """Info about claimed cheque: how much and which coin"""
    status: bool
    coin_id: int
    """which coin has been taken"""
    coin_amount: int
    """how much coins has been taken"""


class PayHistory:
    """Who payed this invoice and when, also have pay's hash"""
    user_id: int
    pay_time: datetime.datetime
    pay_hash: str

    def __init__(self,user_id,pay_time,pay_hash):
        self.user_id = user_id
        self.pay_time = datetime.datetime.fromisoformat(pay_time)
        self.pay_hash = pay_hash


class InvoiceMy:
    """Creator_id, invoice_unique_hash, coin_id, coin_amount, comment, expiration_time, creation_time, return_url"""
    creator_id: int
    invoice_unique_hash: str
    coin_id: int
    coin_amount: int
    comment: str
    expiration_time: datetime.datetime
    creation_time: datetime.datetime
    return_url: str

    def __init__(self,creator_id,invoice_unique_hash,coin_id,coin_amount,comment,expiration_time,creation_time,return_url):
        self.creator_id = creator_id
        self.invoice_unique_hash = invoice_unique_hash
        self.coin_id = coin_id
        self.coin_amount = coin_amount
        self.comment = comment
        self.expiration_time = datetime.datetime.fromisoformat(expiration_time)
        self.creation_time = datetime.datetime.fromisoformat(creation_time)
        self.return_url = return_url
    
    @property
    def is_expired(self):
        cur_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=4), name="Samara")).timestamp()
        return cur_time > self.expiration_time.timestamp()
    
    @property
    def url(self):
        return f"https://t.me/stupidwallet_bot?start={self.invoice_unique_hash}"

    def __str__(self):
        return f"{type(self).__name__}({self.invoice_unique_hash} id{self.coin_id}*{self.coin_amount})"

    def __repr__(self):
        return f"""{type(self).__name__}({dict([(name, getattr(self, name)) for name in dir(self) if name[0] != "_"])})"""


class InvoiceInfo(InvoiceMy):
    """Status, creator_id, invoice_unique_hash, coin_id, coin_amount, comment, expiration_time, creation_time, return_url, pay_history"""
    status: bool
    creator_id: int
    invoice_unique_hash: str
    coin_id: int
    coin_amount: int
    comment: str
    expiration_time: datetime.datetime
    creation_time: datetime.datetime
    return_url: str
    pay_history: list[PayHistory] | list

    def __init__(self,status,creator_id,invoice_unique_hash,coin_id,coin_amount,comment,expiration_time,creation_time,return_url,pay_history):
        self.status = status
        self.creator_id = creator_id
        self.invoice_unique_hash = invoice_unique_hash
        self.coin_id = coin_id
        self.coin_amount = coin_amount
        self.comment = comment
        self.expiration_time = datetime.datetime.fromisoformat(expiration_time)
        self.creation_time = datetime.datetime.fromisoformat(creation_time)
        self.return_url = return_url
        self.pay_history = [PayHistory(**x) for x in pay_history]

    @property
    def is_payed(self): return len(self.pay_history) > 0

    def __str__(self): return f"{type(self).__name__}({self.invoice_unique_hash} id{self.coin_id}*{self.coin_amount})"

    def __repr__(self): return f"""{type(self).__name__}({dict([(name, getattr(self, name)) for name in dir(self) if name[0] != "_"])})"""


class Wallet:
    _client: httpx.AsyncClient
    
    def __init__(self, api_key: str, base_url: str = "https://swapi.physm.org"):
        self._client = httpx.AsyncClient(base_url=base_url, headers={"api-key": api_key})
    
    async def _get_req(self, path, act: Literal["post", "get", "delete"] = "get", **kwargs) -> dict:
        if act == "post":
            r = await self._client.post(url=path, **kwargs)
        elif act == "get":
            r = await self._client.get(url=path, **kwargs)
        elif act == "delete":
            r = await self._client.delete(url=path, **kwargs)
        else:
            raise ValueError(f'Excepted "post", "get", "delete", not {act!r}!')
        await asyncio.sleep(0.33)
        return r.json()
    
    async def check_expired_invoices(self):
        """
        Check if invoices expiration time < current time
        if it is, delete this invoice
        """
        invoices = (await self.get_all_invoices())
        for _invoice in invoices:
            await self.check_expired_invoice(_invoice)
    
    async def is_invoice_expired(self, invoice: Union[InvoiceMy, InvoiceInfo, str]):
        """Returns None if invalid invoice"""
        return await self.check_expired_invoice(invoice)
    
    async def check_expired_invoice(self, invoice: Union[InvoiceMy, InvoiceInfo, str]) -> bool:
        """Check invoice's expiration time

        Args:
            invoice (Union[InvoiceMy, InvoiceInfo, str]): Which invoice need in check

        Returns:
            bool: Invoice is expired or not
        """
        if isinstance(invoice, str):
            assert isinstance(invoice, str), "wth"
            invoice = await self.check_invoice(invoice)
        
        if invoice.is_expired:
            status = await self.delete_invoice(invoice.invoice_unique_hash)
            return True
        return False
    
    async def get_balance(self, coin_id: int) -> dict:
        """Get balance of WAV/TWAV

        Args:
            coin_id (int): 1 — WAV, 2 — TWAV

        Returns:
            dict: info about balance or error message
        """
        result = await self._get_req("/user/get_balance", params=dict(coin_id=coin_id))
        return result
    
    async def clear_invoices(self) -> None:
        """
        Just delete all invoices
        """
        for invoice_current in (await self.get_all_invoices()):
            await self.delete_invoice(invoice_current.invoice_unique_hash)
    
    async def delete_invoice(self, unique_hash: str) -> bool:
        """Delete some invoice by his unique hash

        Args:
            unique_hash (str): Invoice's unique hash

        Returns:
            bool: Delete is success or not
        """
        response = await self._get_req(f"/invoice/delete_invoice", act="delete", params=dict(invoice_unique_hash=unique_hash))
        result = response.get('status', 'False')
        return result
    
    async def get_all_invoices(self) -> list[InvoiceMy]:
        """
        Get all invoices in dict
        """
        response = await self._get_req("/invoice/my_invoices")
        if response.get('error'):
            raise Exception(str(response))
        invoices = [InvoiceMy(**inv) for inv in response['data']]
        return invoices
    
    # invoice/счёт
    async def create_invoice(self, coin_id: int, coin_amount: int, expiration_time: int = 60, comment="", return_url="") -> InvoiceInfo:
        """
        Create invoice and return his hash in dict
        :param coin_id: integer 1 for WAV and 2 for TWAV
        :param coin_amount: number of coins to pay the invoice
        :param expiration_time: minutes for the invoice to be overdue.
        :param comment: comment on the invoice
        :param return_url: redirects there when you click on the "return" button
        :return: dictionary with status and invoice hash
        :rtype:
        """
        response = await self._get_req('/invoice/create_invoice', act="post", params=dict(coin_id=coin_id, coin_amount=coin_amount, expiration_time=expiration_time, comment=comment, return_url=return_url if return_url else ""))
        if response.get('error'):
            raise Exception(str(response))
        
        invoice_id: str = response['invoice_unique_hash']
    
        if invoice_id is None:
            await self.check_expired_invoices()
            response = await self._get_req('/invoice/create_invoice', act="post", params=dict(coin_id=coin_id, coin_amount=coin_amount, expiration_time=expiration_time, comment=comment, return_url=return_url if return_url else ""))
            if response.get('error'):
                raise Exception(str(response))
            
            invoice_id = response['invoice_unique_hash']
        
        result = await self.check_invoice(invoice_id)
        # LOGGER.info(str(locals()))
        return result
    
    async def pay_invoice(self, unique_hash: str) -> bool:
        """Pay invoice"""
        response = await self._get_req(f"/invoice/pay_invoice", act="post", params=dict(invoice_unique_hash=unique_hash))
        result = response.get('status', False)
        return result
    
    async def check_invoice(self, unique_hash: str) -> InvoiceInfo:
        """Return InvoiceInfo or None if invalid"""
        response = await self._get_req(f"/invoice/get_invoice_data", params=dict(invoice_unique_hash=unique_hash))
        if response.get('error'):
            raise Exception(str(response))
        
        result = InvoiceInfo(**response)
        return result
    
    async def wait_pay_invoice(self, unique_hash: str) -> Union[bool, None]:
        """Ожидает оплаты счёта в течении минуты. Если ожидаемого счёта не существует, возвращает None, иначе если оплачен счёт и он не просрочен, возвращает True, иначе False"""
        invoice = await self.check_invoice(unique_hash)
        if invoice is None: return None
        
        while not (invoice.is_payed or invoice.is_expired):
            await asyncio.sleep(1)
            invoice = await self.check_invoice(unique_hash)
        
        return invoice.is_payed
    
    # Cheque / чек
    async def create_cheque(self, coin_id: int, coin_amount: int, comment="*комментарий к чеку*") -> Cheque:
        """Создаёт чек и возвращает его"""
        cheque_id = (await self._get_req(f'/user/create_cheque', act="post", params=dict(coin_id=coin_id,coin_amount=coin_amount,comment=comment)))['cheque_id']
        result = await self.check_cheque(cheque_id)
        return result
    
    async def claim_cheque(self, cheque_id: str, password: str = '') -> ChequeClaimed:
        response = await self._get_req(f"/user/claim_cheque", act="post", params=dict(cheque_id=cheque_id, password=password))
        if response.get('error'):
            raise Exception(str(response))
        result = ChequeClaimed(**response)
        return result
    
    async def check_cheque(self, cheque_id: str) -> Cheque:
        response = await self._get_req(f"/user/info_cheque", params=dict(cheque_id=cheque_id))
        if response.get('error'):
            raise Exception(str(response))
        result = Cheque(**response)
        result.add_hash(cheque_id)
        return result