# Wwise Authoring API (Waapi) Client for Python
Decoupled autobahn WAMP client with support for plain options and bindable subscription callbacks.

## Requirements
* Python 3.7, 3.8 or 3.9
* Wwise instance with the Wwise Authoring API enabled (`Project > User Preferences... > Enable Wwise Authoring API`)

## Setup
For compatibility with Python 2 on Windows, it is recommended to use the [Python Launcher for Windows](https://docs.python.org/3/using/windows.html#launcher) which is installed with Python 3 from [python.org](https://www.python.org).

* Windows: `py -3 -m pip install waapi-client` 
* Other platforms: `python3 -m pip install waapi-client`

## Usage
```python
from waapi import WaapiClient

with client as WaapiClient()
    result = client.call("ak.wwise.core.getInfo")
```

The `with` statement automatically closes the connection and unregisters subcribers.
To keep the connection alive, instantiate `WaapiClient` and call `disconnect` when you are done.

```python
from waapi import WaapiClient

# Connect (default URL)
client = WaapiClient()

# RPC
result = client.call("ak.wwise.core.getInfo")

# Subscribe
handler = client.subscribe(
    "ak.wwise.core.object.created",
    lambda object: print("Object created: " + str(object))
)

# Bind a different callback at any time
def my_callback(object):
    print("Different callback: " + str(object))

handler.bind(my_callback)

# Unsubscribe
handler.unsubscribe()

# Disconnect
client.disconnect()
```

Be aware that failing to call `disconnect` will result in the program to appear unresponsive, as the background thread
running the connection will remain active.

## Contribute
This repository accepts pull requests.
You may open an [issue](https://github.com/audiokinetic/waapi-client-python/issues) for any bugs or improvement requests.

### Local Install
You may install the package locally using either pip or pipenv.

Clone this repository, then from the repository root run:

* Windows: `py -3 -m pip install -e .` 
* Other platforms: `python3 -m pip install -e .`

or

`pipenv install --three`

### Running the Tests
Install the `tox` package:

* Windows: `py -3 -m pip install tox`
* Other platforms: `python3 -m pip install tox`

Open a blank project in Wwise, then you may execute `tox` in the terminal from the root of the repository

The test suite will run for all supported versions of Python.
Use `-e pyXX` to run for a single version, e.g., `tox -e py37` for Python 3.7).