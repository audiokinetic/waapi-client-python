import time
from pprint import pprint

from waapi.client import WaapiClient

client = WaapiClient.connect()

while not client:
    print("Cannot connect, retrying in 1 second...")
    time.sleep(1)
    client = WaapiClient.connect()

assert(client.has_client())

print("Ready!")

todo = None
while True:
    todo = input("What do you want to do? ")

    todo = todo.lower()
    if todo == "getinfo":
        response = client.call("ak.wwise.core.getInfo")
        # assert(response is not None)
        pprint(response)
    elif todo == "quit" or todo == "exit":
        break


print("Done!")
client.disconnect()
print("Disconnected!")
