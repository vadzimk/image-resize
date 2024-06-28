from dataclasses import dataclass

from ..request_model import ProjectProgressSchema, GetProjectSchema, ProjectFailureSchema


class Event:
    pass


@dataclass
class CeleryTaskUpdated(Event):
    message: ProjectProgressSchema


@dataclass
class CeleryTaskFailed(Event):
    message: ProjectFailureSchema


@dataclass
class OriginalUploaded(Event):
    message: GetProjectSchema
