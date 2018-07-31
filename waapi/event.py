from waapi.interface import UnsubscribeHandler


class EventHandler:
    """
    Manager of a WAMP subscription with a function handler when an event is received and a mean to unsubscribe
    """
    def __init__(self, unsubscribe_handler=None, callback=None):
        """
        :param unsubscribe_handler: UnsubscribeHandler
        :param callback: (Any) -> None
        """
        self.unsubscribe_handler = unsubscribe_handler
        self._callback = callback
        self._subscription = None

    @property
    def subscription(self):
        return self._subscription

    @subscription.setter
    def subscription(self, value):
        if value is not None:
            self._subscription = value

    def unsubscribe(self):
        if not self.unsubscribe_handler:
            return False

        return self.unsubscribe_handler.unsubscribe(self)

    def on_event(self, *args, **kwargs):
        if self._callback:
            self._callback(*args, **kwargs)

    def bind(self, callback):
        if self._callback and callable(self._callback):
            self._callback = callback
            return self

    def __call__(self, *args, **kwargs):
        self.on_event(*args, **kwargs)
