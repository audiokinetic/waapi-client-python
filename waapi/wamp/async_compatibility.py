
import six
if six.PY2:
    # Support python2 asyncio
    import trollius as _asyncio
else:
    import asyncio as _asyncio

asyncio = _asyncio

import txaio
txaio.use_asyncio()
