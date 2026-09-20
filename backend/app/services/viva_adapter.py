class VivaNotImplementedError(NotImplementedError):
    pass


async def sync_viva(*_args, **_kwargs) -> int:
    raise VivaNotImplementedError("Viva Wallet sync is not available in MVP")
