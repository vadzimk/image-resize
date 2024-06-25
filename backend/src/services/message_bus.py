import logging
from typing import Union

from ..domain import commands
from ..domain import events

logger = logging.getLogger(__name__)

Message = Union[commands.Command, events.Event]


class MessageBus:
    def __init__(self, event_handlers, command_handlers):
        self.queue = []
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers

    def handle_event(self, event: events.Event):
        logger.info(f"Handling event {event}")
        for handler in self.event_handlers[type(event)]:
            try:
                handler(event)
            except Exception:
                logger.exception(f"Exception handling event {event}")
                raise

    def handle_command(self, command: commands.Command):
        logger.info(f"Handling command {command}")
        try:
            handler = self.command_handlers[type(command)]
            handler(command)
        except Exception:
            logger.exception(f"Exception handling command {command}")
            raise

    def handle(self, message: Message):
        logger.info(f"bus:handle:message: {message}")
        self.queue.append(message)
        while self.queue:
            cur_message = self.queue.pop(0)
            if isinstance(cur_message, events.Event):
                self.handle_event(cur_message)
            elif isinstance(cur_message, commands.Command):
                self.handle_command(cur_message)
            else:
                raise Exception(f"`message` must be instance of Event or Command got {type(message)}")
