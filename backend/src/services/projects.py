"""
domain object model
"""


class ProjectDOM:
    def __init__(self, *, project_id, state, versions, progress=None):
        self.project_id = project_id
        self.state = state
        self.versions = versions
        self.progress = progress

    def dict(self):
        return {
            "project_id": self.project_id,
            "state": self.state,
            "versions": self.versions,
            "progress": self.progress,
        }
