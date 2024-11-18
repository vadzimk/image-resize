import asyncio
import inspect
import logging
from typing import Union, Dict, Callable

from . import handlers
from ..models.domain import commands, events

logger = logging.getLogger(__name__)

Message = Union[commands.Command, events.Event]


class MessageBus:
    def __init__(self, event_handlers, command_handlers):
        self._loop = None
        self.queue = []
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, loop):
        self._loop = loop

    async def _handle_event(self, event: events.Event):
        logger.debug(f"Handling event {event}")
        for handler in self.event_handlers[type(event)]:
            try:
                await handler(event)
            except Exception:
                logger.error(f"Exception handling event {event}")
                raise

    async def _handle_command(self, command: commands.Command):
        logger.debug(f"Handling command {command}")
        try:
            handler = self.command_handlers[type(command)]
            await handler(command)
        except Exception:
            logger.error(f"Exception handling command {command}")
            raise

    def handle(self, message: Message):
        logger.debug(f"message: {message}")
        self.queue.append(message)
        while self.queue:
            cur_message = self.queue.pop(0)
            if isinstance(cur_message, events.Event):
                asyncio.run_coroutine_threadsafe(
                    self._handle_event(cur_message), loop=self.loop)
            elif isinstance(cur_message, commands.Command):
                asyncio.run_coroutine_threadsafe(
                    self._handle_command(cur_message), loop=self.loop)
            else:
                raise Exception(f"`message` must be instance of Event or Command got {type(message)}")


def create_bus() -> MessageBus:
    dependencies: Dict[str, Callable] = {}  # for future use, additional instantiated dependencies that are passed to handlers as kwargs
    injected_event_handlers = {
        event_type: [inject_dependencies(handler, dependencies) for handler in event_handlers]
        for event_type, event_handlers in handlers.event_handlers.items()
    }
    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies)
        for command_type, handler in handlers.command_handlers.items()
    }
    return MessageBus(
        event_handlers=injected_event_handlers,
        command_handlers=injected_command_handlers
    )


def inject_dependencies(handler, dependencies):
    params = inspect.signature(handler).parameters
    deps = {name: dependency for name, dependency in dependencies.items() if name in params}
    return lambda message: handler(message, **deps)


bus = create_bus()
