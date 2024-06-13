from ..exceptions import ProjectNotFoundError
from ..repository.projects_repository import ProjectsRepositoryInterface
from .projects import ProjectDOM


class ProjectsService:
    def __init__(self, projects_repository: ProjectsRepositoryInterface):
        self.projects_repository = projects_repository

    def get_project(self, project_id) -> ProjectDOM:
        project = self.projects_repository.get(project_id)
        if project is not None:
            return project
        raise ProjectNotFoundError(project_id)
