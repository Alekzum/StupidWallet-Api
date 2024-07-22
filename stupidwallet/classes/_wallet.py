from typing import Union, Literal, Optional
import datetime
import asyncio
import httpx


class ChequeMy:
    def __init__(self, source: dict):
        self.coin_id: int = source['coin_id']
        self.coin_amount: int = source['coin_amount']
        self.password: str = source['password']
        self.cheque_id: str = source['cheque_id']
        self.comment: str = source['comment']

    def __str__(self):
        return f"<Cheque {self.cheque_id} id{self.coin_id}*{self.coin_amount}>"

    def __repr__(self):
        return f"""{type(self).__name__}({dict([(name, getattr(self, name)) for name in dir(self) if name[0] != "_"])})"""


class Cheque(ChequeMy):
    def __init__(self, source: dict):
        self.status: bool = source['status']
        self.coin_id: int = source['coin_id']
        self.coin_amount: int = source['coin_amount']
        self.is_activated: bool = source['is_activated']
        self.has_password: bool = source['has_password']
        self.comment: str = source['comment']
        self.cheque_id: str = source['cheque_id']
    
    def __str__(self):
        return f"<Cheque {self.cheque_id} is_activated={self.is_activated} id{self.coin_id}*{self.coin_amount}>"

    def add_hash(self, hash: str):
        self.cheque_id = hash


class ChequeClaimed:
    def __init__(self, source: dict):
        self.status: bool = source['status']
        self.coin_id: int = source['coin_id']
        self.coin_amount: int = source['coin_amount']


class PayHistory:
    def __init__(self, source: dict):
        self.user_id: int = source['user_id']
        _pay_time = source['pay_time']
        self.pay_time: Optional[datetime.datetime] = datetime.datetime.fromisoformat(_pay_time) if _pay_time else None
        self.pay_hash: str = source['pay_hash']


class Invoice:
    def __init__(self, source: dict):
        self.invoice_unique_hash: str = source['invoice_unique_hash']
        self.coin_id: int = source['coin_id']
        self.coin_amount: int = source['coin_amount']
        self.comment: str = source['comment']
        _expiration_time = source['expiration_time']
        self.expiration_time: Optional[datetime.datetime] = datetime.datetime.fromisoformat(_expiration_time) if _expiration_time else None
        _creation_time = source['_creation_time']
        self.creation_time: Optional[datetime.datetime] = datetime.datetime.fromisoformat(_creation_time) if _creation_time else None
        self.return_url: str = source['return_url']
        self.status: bool = source['status']

    def __str__(self): return f"InvoiceInfo({self.invoice_unique_hash} id{self.coin_id}*{self.coin_amount})"    


class InvoiceMy:
    """Creator_id, invoice_unique_hash, coin_id, coin_amount, comment, expiration_time, creation_time, return_url"""
    def __init__(self, source: dict):
        self.creator_id: int = source['creator_id']
        self.invoice_unique_hash: str = source['invoice_unique_hash']
        self.coin_id: int = source['coin_id']
        self.coin_amount: int = source['coin_amount']
        self.comment: str = source['comment']
        _expiration_time = source['expiration_time']
        self.expiration_time: Optional[datetime.datetime] = datetime.datetime.fromisoformat(_expiration_time) if _expiration_time else None
        _creation_time = source['_creation_time']
        self.creation_time: Optional[datetime.datetime] = datetime.datetime.fromisoformat(_creation_time) if _creation_time else None
        self.return_url: str = source['return_url']
    
    @property
    def is_expired(self):
        cur_time = datetime.datetime.fromtimestamp(datetime.datetime.now().timestamp() - 60*60*1)
        expiration_time = self.expiration_time
        return cur_time > expiration_time

    def __str__(self):
        return f"{type(self).__name__}({self.invoice_unique_hash} id{self.coin_id}*{self.coin_amount})"

    def __repr__(self):
        return f"""{type(self).__name__}({dict([(name, getattr(self, name)) for name in dir(self) if name[0] != "_"])})"""


class InvoiceInfo(InvoiceMy):
    """Status, creator_id, invoice_unique_hash, coin_id, coin_amount, comment, expiration_time, creation_time, return_url, pay_history"""
    def __init__(self, source: dict):
        self.status: bool = source['status']
        self.creator_id: int = source['creator_id']
        self.invoice_unique_hash: str = source['invoice_unique_hash']
        self.coin_id: int = source['coin_id']
        self.coin_amount: int = source['coin_amount']
        self.comment: str = source['comment']
        _expiration_time = source['expiration_time']
        self.expiration_time: Optional[datetime.datetime] = datetime.datetime.fromisoformat(_expiration_time) if _expiration_time else None
        _creation_time = source['_creation_time']
        self.creation_time: Optional[datetime.datetime] = datetime.datetime.fromisoformat(_creation_time) if _creation_time else None
        self.return_url: str = source['return_url']
        _pay_history = source['pay_history']
        self.pay_history: Optional[list[PayHistory]] = list(map(lambda x: PayHistory(x), _pay_history)) if _pay_history else None

    @property
    def is_payed(self): return len(self.pay_history) > 0

    def __str__(self): return f"{type(self).__name__}({self.invoice_unique_hash} id{self.coin_id}*{self.coin_amount})"

    def __repr__(self): return f"""{type(self).__name__}({dict([(name, getattr(self, name)) for name in dir(self) if name[0] != "_"])})"""


class Wallet:
    _client: httpx.AsyncClient
    
    def __init__(self, api_key: str, base_url: str = "https://sw.svat.dev"):
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
        await asyncio.sleep(0.1)
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
    
    async def check_expired_invoice(self, invoice: Union[InvoiceMy, InvoiceInfo, str]) -> Union[bool, None]:
        """Returns None if invalid invoice"""
        if isinstance(invoice, str): 
            assert isinstance(invoice, str), "wth"
            invoice = await self.check_invoice(invoice)
        
        if not isinstance(invoice, InvoiceMy): 
            return None
        if invoice.is_expired:
            status = await self.delete_invoice(invoice.invoice_unique_hash)
            return True
        return False
    
    async def get_balance(self, coin_id: int) -> dict:
        """
        Get balance of WAV/TWAV (coin_id: 1 — WAV, 2 — TWAV)
        :param coin_id: which balance do you need
        :type coin_id: integer
        :return: info about balance or error message
        :rtype: dict
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
        """
        Delete some invoice by his unique hash
        :param unique_hash: Invoice's unique hash
        :type unique_hash: str
        :return: result: True is success else False
        :rtype: bool
        """
        _result = await self._get_req(f"/invoice/delete_invoice", act="delete", params=dict(invoice_unique_hash=unique_hash))
        result = _result['status', 'False']
        return result
    
    async def get_all_invoices(self) -> list[InvoiceMy]:
        """
        Get all invoices in dict
        """
        response = await self._get_req("/invoice/my_invoices")
        invoices = list(map(lambda inv: InvoiceMy(inv), response['data']))
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
        invoice_id: str = response['invoice_unique_hash']
    
        if invoice_id is None:
            await self.check_expired_invoices()
            response = await self._get_req('/invoice/create_invoice', act="post", params=dict(coin_id=coin_id, coin_amount=coin_amount, expiration_time=expiration_time, comment=comment, return_url=return_url if return_url else ""))
            invoice_id = response['invoice_unique_hash']
        
        result = await self.check_invoice(invoice_id)
        # LOGGER.info(str(locals()))
        return result
    
    async def pay_invoice(self, unique_hash: str) -> bool:
        """Pay invoice"""
        _result = await self._get_req(f"/invoice/pay_invoice", act="post", params=dict(invoice_unique_hash=unique_hash))
        result = _result.get('status', False)
        return result
    
    async def check_invoice(self, unique_hash: str) -> InvoiceInfo:
        """Return InvoiceInfo or None if invalid"""
        response = await self._get_req(f"/invoice/get_invoice_data", params=dict(invoice_unique_hash=unique_hash))
        if response.get('status'):
            result = InvoiceInfo(response)
        else:
            raise Exception(str(response))
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
        """"""
        result = ChequeClaimed(await self._get_req(f"/user/claim_cheque", act="post", params=dict(cheque_id=cheque_id, password=password)))
        return result
    
    async def check_cheque(self, cheque_id: str) -> Cheque:
        result = Cheque(await self._get_req(f"/user/info_cheque", params=dict(cheque_id=cheque_id)))
        result.add_hash(cheque_id)
        return result