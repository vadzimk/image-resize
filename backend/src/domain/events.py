from asyncio import AbstractEventLoop
from dataclasses import dataclass

from ..schemas import ProjectProgressSchema, GetProjectSchema


class Event:
    pass


@dataclass
class CeleryTaskUpdated(Event):
    message: ProjectProgressSchema
    loop: AbstractEventLoop


@dataclass
class OriginalUploaded(Event):
    message: GetProjectSchema
    loop: AbstractEventLoop

