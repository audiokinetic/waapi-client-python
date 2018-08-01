# Wwise Authoring API (Waapi) Client for Python
Decoupled autobahn WAMP client with support for plain options and bindable subscription callbacks.

## Requirements
* Python 3.4+
* Wwise instance with the Wwise Authoring API enabled (`Project > User Preferences... > Enable Wwise Authoring API`)

## For users
### Setup
`python3 -m pip install waapi-client`

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

`python3 -m pip -e .` or `pipenv install --three`

### Running the tests
Open a blank project in Wwise, then you may execute the test on terminal from the root of the repository by running:

`python3 -m unittest discover -p "test_*" -v`