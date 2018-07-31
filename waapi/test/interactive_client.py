import time
from pprint import pprint

from waapi.event import EventHandler
from waapi.client import WaapiClient

client = WaapiClient.connect()

while not client:
    print("Cannot connect, retrying in 1 second...")
    time.sleep(1)
    client = WaapiClient.connect()

assert(client.is_connected())

print("Ready!")

event_handlers = []

todo = None
while True:
    todo = input("What do you want to do? ")

    todo = todo.lower()
    if todo == "help":
        print("Defined commands:")
        print("* getinfo")
        print("* sel")
        print("* project")
        print("* note(w)")
        print("* unsub")
        print("* quit/exit")
    elif todo == "getinfo":
        response = client.call("ak.wwise.core.getInfo")
        pprint(response)
    elif todo == "sel":
        def sel_changed(**kwargs):
            print("Selection changed!")

        handler = client.subscribe("ak.wwise.ui.selectionChanged", sel_changed)
        print("Subscribe succeeded" if handler else "Subscribe failed!")
        print(handler)
        event_handlers.append(handler)

    elif todo == "project":
        myargs = {
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
        response = client.call("ak.wwise.core.object.get", **myargs)
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

        handler = client.subscribe(
            "ak.wwise.core.object.notesChanged",
            notes_changed_wrapped if todo.endswith("w") else notes_changed_unwrapped,
            **{"return": ["name"]}
        )
        print("Subscribe succeeded" if handler else "Subscribe failed!")
        print(handler)
        event_handlers.append(handler)
    elif todo == "unsub":
        for sub in client.subscriptions():
            res = sub.unsubscribe()  # or client.unsubscribe(sub)
            print(("Successfully unsubscribed" if res else "Failed to unsubscribe") + " from " + str(sub))

    elif todo == "eh":  # Event Handler subclass
        class MyEventHandler(EventHandler):
            def on_event(self, *args, **kwargs):
                print("MyEventHandler callback!")

        print("Testing callback...")
        event_handler = MyEventHandler()
        event_handler()
        print("Testing done.")
        handler = client.subscribe("ak.wwise.core.object.created", event_handler)
        print(("Successfully subscribed" if handler else "Failed to subscribe") + " to ak.wwise.core.object.created")

    elif todo == "rebind":
        def rebound_callback(*args, **kwargs):
            print("Rebound placeholder callback!")
            pprint(args)
            pprint(kwargs)

        for sub in client.subscriptions():
            sub.bind(rebound_callback)

    elif todo == "quit" or todo == "exit":
        break


print("Done!")
client.disconnect()
print("Disconnected!")
