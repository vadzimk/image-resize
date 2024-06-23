class ClientError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class AlreadySubscribed(ClientError):
    def __init__(self, message="Already Subscribed"):
        super(AlreadySubscribed, self).__init__(message)


class NotInSubscriptions(ClientError):
    def __init__(self, message="Not in subscriptions"):
        super(NotInSubscriptions, self).__init__(message)


class ProjectNotFoundError(ClientError):
    def __init__(self, project_id):
        super(ProjectNotFoundError, self).__init__(f"Project with id {project_id} not found")


class S3ObjectNotFoundError(ClientError):
    def __init__(self, object_key, bucket_name):
        super().__init__(f"S3 object with id {object_key} not found in bucket {bucket_name}")
