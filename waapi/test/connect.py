import time

from waapi.client import WaapiClient

client = WaapiClient.connect()

while not client.has_client():
    print("Not ready...")
    time.sleep(1)

print("Ready!")

todo = None
while not todo:
    todo = input("What do you want to do?")

print("Done!")
client.disconnect()
print("Disconnected!")
