class AlreadySubscribed(Exception):
    def __init__(self, message="Already Subscribed"):
        super(AlreadySubscribed, self).__init__(message)


class NotInSubscriptions(Exception):
    def __init__(self, message="Not in subscriptions"):
        super(NotInSubscriptions, self).__init__(message)
