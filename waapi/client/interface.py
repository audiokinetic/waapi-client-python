class UnsubscribeHandler:
    """
    Abstract service that allows to unsubscribe a EventHandler's subscription
    """
    def unsubscribe(self, event_handler):
        """
        :type event_handler: EventHandler
        :return: True if the unsubscribe was successful, False otherwise.
        :rtype: bool
        """
        raise NotImplementedError()
