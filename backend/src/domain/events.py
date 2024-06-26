from asyncio import AbstractEventLoop
from dataclasses import dataclass

from ..schemas import ProjectProgressSchema, GetProjectSchema


class Event:
    pass


@dataclass
class CeleryTaskUpdated(Event):
    message: ProjectProgressSchema


@dataclass
class OriginalUploaded(Event):
    message: GetProjectSchema

