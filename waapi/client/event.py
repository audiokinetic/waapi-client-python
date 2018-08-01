from autobahn.wamp.request import Subscription


class EventHandler:
    """
    Manager of a WAMP subscription with a function handler when an event is received and a mean to unsubscribe

    This is an abstraction over an autobahn subscription that provides flexibility in callback routing.
    By using the on_event method as the callback, users can change the behavior of this method either by binding a
    callback function (which can change at any point in time) or override on_event in a subclass.

    Constructing an instance of this class before subscription is possible, but the subscription and unsubscribe_handler
    members will be updated to match the client and their reference must remain unchanged to properly handle ownership.

    An instance of this class is also callable and can therefore be use as if it were a function reference.
    """
    def __init__(self, unsubscribe_handler=None, callback=None):
        """
        :param unsubscribe_handler: UnsubscribeHandler | None
        :param callback: (*Any) -> None | None
        """
        self._unsubscribe_handler = unsubscribe_handler
        """:type: UnsubscribeHandler"""

        self._callback = callback

        self._subscription = None
        """
        :type: Subscription | None
        """

    @property
    def subscription(self):
        return self._subscription

    @subscription.setter
    def subscription(self, value):
        if value is None or isinstance(value, Subscription):
            self._subscription = value

    def unsubscribe(self):
        """
        :return: True if the EventHandler was unsubscribed successfully, False otherwise.
        :rtype: bool
        """
        if not self._unsubscribe_handler:
            return False

        return self._unsubscribe_handler.unsubscribe(self)

    def on_event(self, *args, **kwargs):
        """
        Callback on reception of an event related to the subscribed topic
        """
        if self._callback:
            self._callback(*args, **kwargs)

    def bind(self, callback):
        """
        Bind a callable callback to this EventHandler instance that is called by on_event by default.
        When subclassing this class, make sure to define the behavior of this function with regards to how on_event
        behaves.

        :type callback: callable | None
        :return: self if the callback was correctly set, None otherwise.
        :rtype: self | None
        """
        if callback and callable(callback):
            self._callback = callback
            return self

    def __call__(self, *args, **kwargs):
        """
        Delegate to on_event
        """
        self.on_event(*args, **kwargs)
