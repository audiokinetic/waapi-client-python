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
        pprint(response)
    elif todo == "sel":
        def sel_changed(data):
            print("Selection changed!")

        response = client.subscribe("ak.wwise.ui.selectionChanged", sel_changed)
        print("Subscribe succeeded" if response else "Subscribe failed!")
    elif todo == "project":
        args = {
            "from": {
                "ofType": [
                    "Project"
                ]
            },
            "options": {
                "return": [
                    "name",
                    "filePath",
                    "workunit:isDirty"
                ]
            }
        }
        response = client.call("ak.wwise.core.object.get", **args)
        pprint(response)
    elif todo.startswith("note"):
        def notes_changed_unwrapped(object, newNotes, oldNotes):
            print("Notes changed (callback with unwrapped)!")
            pprint(object)
            pprint(newNotes)
            pprint(oldNotes)

        def notes_changed_wrapped(**kwargs):
            print("Notes changed (callback with wrapped)!")
            pprint(kwargs)

        response = client.subscribe(
            "ak.wwise.core.object.notesChanged",
            notes_changed_wrapped if todo.endswith("w") else notes_changed_unwrapped,
            **{"return": ["name"]}
        )

    elif todo == "quit" or todo == "exit":
        break


print("Done!")
client.disconnect()
print("Disconnected!")
