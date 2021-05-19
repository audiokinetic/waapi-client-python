from abc import abstractmethod

class UnsubscribeHandler:
    """
    Abstract service that allows to unsubscribe a EventHandler's subscription
    """
    @abstractmethod
    def unsubscribe(self, event_handler):
        """
        :type event_handler: EventHandler
        :return: True if the unsubscribe was successful, False otherwise.
        :rtype: bool
        """
        raise NotImplementedError()

class CallbackExecutor:
    """
    Abstract executor for a wamp callback, used as a strategy in event handlers
    """
    def start(self):
        pass

    def stop(self):
        pass

    @abstractmethod
    def execute(callback):
        """
        Executes a callback according to the implemented strategy
        Does not guarantee the callback will have been executed upon return
        :type callback: () -> Any
        """
        raise NotImplementedError()
