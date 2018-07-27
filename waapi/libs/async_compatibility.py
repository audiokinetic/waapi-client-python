
import six
if six.PY2:
    # Support python2 asyncio
    import trollius as _asyncio
    def yield_from(to_yield):
        def _from(obj):
            return obj
        # return yield _from(to_yield)
else:
    import asyncio as _asyncio
    def yield_from(to_yield):
        res = yield from to_yield
        return res

asyncio = _asyncio