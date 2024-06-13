class AlreadySubscribed(Exception):
    def __init__(self, message="Already Subscribed"):
        super(AlreadySubscribed, self).__init__(message)


class NotInSubscriptions(Exception):
    def __init__(self, message="Not in subscriptions"):
        super(NotInSubscriptions, self).__init__(message)


class ProjectNotFoundError(Exception):
    def __init__(self, project_id):
        super(ProjectNotFoundError, self).__init__(f"Project with id {project_id} not found")
