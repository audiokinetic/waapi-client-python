# Wwise Authoring API (Waapi) Client for Python
Decoupled autobahn WAMP client with support for plain options and bindable subscription callbacks.

## Requirements
* Python 3.4+ (IMPORTANT: 3.7 is not yet supported, awaiting [fix from autobahn](https://github.com/crossbario/autobahn-python/issues/1022) to be released)
* Wwise instance with the Wwise Authoring API enabled (`Project > User Preferences... > Enable Wwise Authoring API`)

## For users
### Setup
For compatibility with Python 2 on Windows, it is recommended to use the [Python Launcher for Windows](https://docs.python.org/3/using/windows.html#launcher) which is installed with Python 3 from [python.org](https://www.python.org).

* Windows: `py -3 -m pip install waapi-client` 
* Other platforms: `python3 -m pip install waapi-client`

### Usage
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

## For developers
### Setup
You may install the package locally using either pip or pipenv.

Clone this repository, then from the repository root run:

* Windows: `py -3 -m pip install -e .` 
* Other platforms: `python3 -m pip install -e .`

or

`pipenv install --three`

### Running the tests
Open a blank project in Wwise, then you may execute the test on terminal from the root of the repository by running:

* Windows: `py -3 setup.py test` 
* Other platforms: `python3 setup.py test`