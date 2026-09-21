"""Bounded TTL cache with per-key single-flight and isolated return values."""
from collections import OrderedDict
from concurrent.futures import Future
from copy import deepcopy
from threading import RLock
from time import monotonic


class ReadCache:
    def __init__(self, capacity=256, clock=monotonic):
        self.capacity, self.clock = capacity, clock
        self._values, self._pending = OrderedDict(), {}
        self._lock = RLock()
        self._generation = 0
        self.hits = self.loads = self.waits = 0

    def get(self, key, ttl, loader):
        with self._lock:
            cached = self._values.get(key)
            if cached and cached[0] > self.clock():
                self._values.move_to_end(key)
                self.hits += 1
                return deepcopy(cached[1])
            self._values.pop(key, None)
            generation = self._generation
            pending_key = (generation, key)
            future = self._pending.get(pending_key)
            owner = future is None
            if owner:
                future = self._pending[pending_key] = Future()
                self.loads += 1
            else:
                self.waits += 1
        if not owner:
            return deepcopy(future.result())
        try:
            value = loader()
            with self._lock:
                if generation == self._generation:
                    self._values[key] = (self.clock() + ttl, deepcopy(value))
                    while len(self._values) > self.capacity:
                        self._values.popitem(last=False)
            future.set_result(value)
            return deepcopy(value)
        except BaseException as error:
            future.set_exception(error)
            raise
        finally:
            with self._lock:
                self._pending.pop(pending_key, None)

    def clear(self):
        with self._lock:
            self._generation += 1
            self._values.clear()
