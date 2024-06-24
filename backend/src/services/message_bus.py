import logging
from typing import Union

from ..domain import commands
from ..domain import events

Message = Union[commands.Command, events.Event]

logger = logging.getLogger(__name__)


class MessageBus:
    def __init__(self, event_handlers, command_handlers):
        self.queue = []
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers

    def handle_event(self, event: events.Event):
        raise NotImplementedError()

    def handle_command(self, command: commands.Command):
        logger.debug(f"Handling command {command}")
        try:
            handler = self.command_handlers[type(command)]
            result = handler(command)
        except Exception:
            logger.exception(f"Exception handling command {command}")
            raise

    def handle(self, message: Message):
        self.queue.append(message)
        while self.queue:
            cur_message = self.queue.pop(0)
            if isinstance(cur_message, events.Event):
                self.handle_event(cur_message)
            elif isinstance(cur_message, commands.Command):
                self.handle_command(cur_message)
            else:
                raise Exception(f"`message` must be instance of Event or Command got {type(message)}")
