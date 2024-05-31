
class AlreadySubscribed(Exception):
    def __init__(self, message="Already Subscribed"):
        super(AlreadySubscribed, self).__init__(message)