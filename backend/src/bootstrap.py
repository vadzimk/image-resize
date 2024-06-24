import inspect
from typing import Callable, Dict

from .services import message_bus, handlers


def bootstrap() -> message_bus.MessageBus:
    dependencies: Dict[str, Callable] = {}  # for future use
    injected_event_handlers = {event_type: [inject_dependencies(handler, dependencies) for handler in event_handlers] for event_type, event_handlers in handlers.event_handlers.items()}
    injected_command_handlers = {command_type: inject_dependencies(handler, dependencies) for command_type, handler in handlers.command_handlers.items()}
    return message_bus.MessageBus(event_handlers=injected_event_handlers, command_handlers=injected_command_handlers)


def inject_dependencies(handler, dependencies):
    params = inspect.signature(handler).parameters
    deps = {name: dependency for name, dependency in dependencies.items() if name in params}
    return lambda message: handler(message, **deps)