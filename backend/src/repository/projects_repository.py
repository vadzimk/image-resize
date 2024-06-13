from abc import ABC, abstractmethod
from typing import List

from ..services.projects import ProjectDOM


class ProjectsRepositoryInterface(ABC):
    @abstractmethod
    def add(self) -> ProjectDOM:
        pass

    @abstractmethod
    def get(self, project_id) -> ProjectDOM | None:
        pass

    @abstractmethod
    def update(self) -> ProjectDOM:
        pass

    @abstractmethod
    def list(self) -> List[ProjectDOM]:
        pass


class ProjectsRepository(ProjectsRepositoryInterface):
    def list(self) -> List[ProjectDOM]:
        pass

    def add(self) -> ProjectDOM:
        pass

    def update(self) -> ProjectDOM:
        pass

    def get(self, project_id) -> ProjectDOM | None:
        # TODO replace hardcoded
        project = {'project_id': project_id,
                'state': 'SUCCESS',
                'versions': {'big_1920': f'{project_id}/photo_big_1920.jpeg',
                             'big_thumb': f'{project_id}/photo_big_thumb.jpeg',
                             'd2500': f'{project_id}/photo_d2500.jpeg',
                             'original': f'{project_id}/photo_original.jpeg',
                             'thumb': f'{project_id}/photo_thumb.jpeg'}}
        return ProjectDOM(**project)
