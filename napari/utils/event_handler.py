import logging
from collections import defaultdict
from typing import Callable, DefaultDict, Set, Any
from napari.utils.event import Event
import inspect

logger = logging.getLogger(__name__)

CALLBACK_MARKER = '_callback_on'


class CallOn:
    def __getattr__(self, value):
        def decorator(func):
            setattr(func, CALLBACK_MARKER, value)
            return func

        return decorator


call_on = CallOn()


class EventHandler:
    def __init__(self, component=None):
        """Event handler for controlling the flow and updates for events.

        For example. for layer specific events it receives change events made
        from the data, controls, or visual interface and updates all associated
        components.
        """
        self.components_to_update = [component] if component else []
        self._callbacks: DefaultDict[Set[Callable]] = defaultdict(set)

    def connect(self, event_name: str, callback: Callable):
        if not callable(callback):
            raise TypeError('`callback` must be a callable function')
        self._callbacks[event_name].add(callback)

    def discover_connections(self, namespace: Any):
        for name in dir(namespace):
            method = getattr(namespace, name, None)
            if not inspect.isroutine(method):
                continue
            event_name = getattr(method, CALLBACK_MARKER, None)
            if not (isinstance(event_name, str) and event_name):
                continue
            self.connect(event_name, method)

    def on_change(self, event: Event):
        """Process an event from any of our event emitters.

        Parameters
        ----------
        event : napari.utils.event.Event
            Event emitter by any of our event emitters. Event must have a
            'type' that indicates the 'name' of the event, and a 'value'
            that carries the data associated with the event. These are
            automatically added by our event emitters.
        """
        type_ = event.type
        logger.debug(f"event: {type_}")
        # until refactor on all layers is complete, not all events will have a
        # value property
        if not hasattr(event, 'value'):
            logger.debug(
                f"Cannot handle event {type_}, without 'value' attribute"
            )
            return
        logger.debug(f" value: {event.value}")
        for callback in self._callbacks[type_]:
            callback(event.value)
