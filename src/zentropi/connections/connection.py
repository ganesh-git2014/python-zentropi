# coding=utf-8

from typing import List
from typing import Optional


class Connection(object):
    def __init__(self):
        self._connected = False
        self._endpoint = None

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def endpoint(self) -> Optional[str]:
        return self._endpoint

    def connect(self, endpoint: str) -> None:  # type: ignore
        raise NotImplementedError()

    def bind(self, endpoint: str) -> None:  # type: ignore
        raise NotImplementedError()

    def close(self) -> None:
        raise NotImplementedError()

    def broadcast(self, frame) -> bool:
        raise NotImplementedError()

    def join(self, space: str) -> bool:  # type: ignore
        raise NotImplementedError()

    def leave(self, space: str) -> bool:
        raise NotImplementedError()

    def spaces(self) -> List[str]:
        raise NotImplementedError()

    def agents(self, space: str) -> List[str]:
        raise NotImplementedError()

    def describe(self, *, space: str, agent: Optional[str] = None) -> dict:
        raise NotImplementedError()
