from asyncio import AbstractEventLoop
from dataclasses import dataclass

from ..schemas import ProjectProgressSchema


class Event:
    pass


@dataclass
class CeleryTaskUpdated(Event):
    message: ProjectProgressSchema
    loop: AbstractEventLoop
