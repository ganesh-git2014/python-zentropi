# coding=utf-8
import asyncio
# import atexit
import threading
from inspect import isgeneratorfunction
from typing import Optional, Union

from pybloom_live import ScalableBloomFilter

from zentropi.frames import Event, Frame, Message
from zentropi.handlers import Handler
from zentropi.symbols import KINDS
from zentropi.timer import TimerRegistry
from zentropi.zentropian import (
    Zentropian,
    on_event,
    on_message,
    on_state
)


class Agent(Zentropian):
    def __init__(self, name=None):
        self.timers = TimerRegistry(callback=self._trigger_frame_handler)
        super().__init__(name=name)
        self.states.should_stop = False
        self.states.running = False
        self.loop = None  # asyncio.get_event_loop()
        self._spawn_on_start = set()
        self._seen_frames = ScalableBloomFilter(
                    mode=ScalableBloomFilter.LARGE_SET_GROWTH, error_rate=0.001)

    @on_state('should_stop')
    def _on_should_stop(self, state):
        if state.data.last is False and state.data.value is True:  # skip double close
            self.close()
        return True

    async def _run_forever(self):
        # atexit.register(self.loop.close)
        if self._spawn_on_start:
            [self.spawn(coro) for coro in self._spawn_on_start]
            self._spawn_on_start = None
        self.emit('*** started', internal=True)
        self.timers.start_timers(self.spawn)
        while self.states.should_stop is False:
            await asyncio.sleep(1)
        self.emit('*** stopped', internal=True)

    def _set_asyncio_loop(self, loop=None):
        if self.loop and loop:
            raise AssertionError('Agent already has an event loop set.')
        if loop:
            self.loop = loop
        if not self.loop:
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()

    def _trigger_frame_handler(self, frame: Frame, handler: Handler, internal=False):
        if isinstance(frame, Message) and frame.source == self.name:
            return
        if isinstance(frame, Event) and frame.source != self.name and frame.name.startswith('***'):
            return
        if frame and frame.id in self._seen_frames:
            return
        if not self.apply_filters([handler]):
            return
        if frame:
            self._seen_frames.add(frame.id)
        payload = []  # type: list
        if handler.pass_self:
            payload.append(self)
        if handler.kind != KINDS.TIMER:
            payload.append(frame)
        if handler.run_async:
            async def return_handler():
                ret_val = await handler(*payload)
                if ret_val:
                    self.handle_return(frame, return_value=ret_val)

            self.spawn(return_handler())
        else:
            ret_val = handler(*payload)
            if ret_val:
                return self.handle_return(frame, return_value=ret_val)

    def add_handler(self, handler):
        if handler.kind == KINDS.TIMER:
            self.timers.add_handler(handler.name, handler)
        else:
            super().add_handler(handler)

    def on_timer(self, interval):
        def wrapper(handler):
            name = str(interval)
            handler_obj = Handler(kind=KINDS.TIMER, name=name, handler=handler)
            self.timers.add_handler(name, handler_obj)
            return handler

        return wrapper

    @staticmethod
    def sleep(duration: float):
        return asyncio.sleep(duration)

    def start(self, loop=None):
        self._set_asyncio_loop(loop)
        self.loop.create_task(self._run_forever())

    def run(self):
        self._set_asyncio_loop()
        self.loop.run_until_complete(self._run_forever())

    def spawn(self, coro):
        if not self.loop:
            self._spawn_on_start.add(coro)
            return
        return self.loop.create_task(coro)

    @staticmethod
    def spawn_in_thread(func, *args, **kwargs):
        task = threading.Thread(target=func, args=args, kwargs=kwargs)
        task.start()
        return task

    def run_in_thread(self):
        return self.spawn_in_thread(self.run)

    def stop(self):
        self.emit('*** stopping', internal=True)
        self.states.should_stop = True
        self.timers.should_stop = True

    def connect(self, endpoint, *, auth=None, tag='default'):
        retval = super().connect(endpoint, auth=auth, tag=tag)
        if not isgeneratorfunction(retval):
            return
        self.spawn(retval)

    def bind(self, endpoint, *, tag='default'):
        retval = super().bind(endpoint, tag=tag)
        if not isgeneratorfunction(retval):
            return
        self.spawn(retval)

    def join(self, space, *, tags: Optional[Union[list, str]] = None):
        retval = super().join(space, tags=tags)
        if not isgeneratorfunction(retval):
            return
        self.spawn(retval)

    def leave(self, space, *, tags: Optional[Union[list, str]] = None):
        retval = super().leave(space, tags=tags)
        if not isgeneratorfunction(retval):
            return
        self.spawn(retval)

    def close(self, *, endpoint: Optional[str] = None, tags: Optional[Union[list, str]] = None):
        """Closes all connections if no endpoint or tags given."""
        if endpoint and tags:
            raise ValueError('Expected either endpoint: {!r} or tags: {!r}.'
                             ''.format(endpoint, tags))
        elif endpoint:
            connections = self._connections.connections_by_endpoint(endpoint)
        elif tags:
            connections = self._connections.connections_by_tags(tags)
        else:
            connections = self._connections.connections
        for connection in connections:
            connection.close()


def on_timer(interval, **kwargs):
    def wrapper(handler):
        name = str(interval)
        handler_obj = Handler(kind=KINDS.TIMER, name=name, handler=handler, **kwargs)
        if hasattr(handler, 'meta'):
            handler.meta.append(handler_obj)
        else:
            handler.meta = [handler_obj]
        return handler

    return wrapper


__all__ = [
    'Agent',
    'on_event',
    'on_message',
    'on_state',
    'on_timer',
]
