from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from types import SimpleNamespace
import pytest
from app.services.cache import ReadCache
from app.services.retry import GoogleExecutor
from app.models.errors import GoogleUnavailable, WriteUncertain


class HttpFailure(Exception):
    def __init__(self,status):
        self.resp=SimpleNamespace(status=status)


def test_ttl_copies_eviction_and_invalidation():
    now=[0]
    cache=ReadCache(2,lambda:now[0])
    calls=[]
    def load(): calls.append(1); return [1]
    a=cache.get("a",10,load); a.append(2)
    assert cache.get("a",10,load)==[1]
    now[0]=10
    cache.get("a",10,load)
    assert len(calls)==2
    cache.get("b",10,load); cache.get("c",10,load)
    cache.get("a",10,load)
    assert len(calls)==5
    cache.clear(); cache.get("a",10,load)
    assert len(calls)==6


@pytest.mark.parametrize("fail",[False,True])
def test_singleflight_shares_success_or_error(fail):
    cache=ReadCache()
    entered, release=Event(),Event()
    calls=[]
    def load():
        calls.append(1);entered.set()
        assert release.wait(5)
        if fail: raise ValueError("fallo compartido")
        return ["ok"]
    with ThreadPoolExecutor(20) as pool:
        first=pool.submit(cache.get,"x",10,load)
        assert entered.wait(5)
        others=[pool.submit(cache.get,"x",10,load) for _ in range(19)]
        # Wait until waiters have attached, not just been submitted.
        from time import monotonic,sleep
        until=monotonic()+5
        while cache.waits<19 and monotonic()<until:sleep(.001)
        assert cache.waits==19
        release.set()
        for task in [first]+others:
            if fail:
                with pytest.raises(ValueError):task.result()
            else: assert task.result()==["ok"]
    assert len(calls)==1
    if fail: assert cache.get("x",10,lambda:["recovered"])==["recovered"]


@pytest.mark.parametrize("statuses",[[429,200],[429,429,200],[429,429,429,429],[500,502,503,200]])
def test_bounded_retries(statuses):
    sleeps=[]; executor=GoogleExecutor(sleep=sleeps.append,jitter=lambda:.25)
    responses=iter(statuses)
    def call():
        status=next(responses)
        if status!=200:raise HttpFailure(status)
        return "ok"
    if statuses[-1]==200:assert executor.execute(call)=="ok"
    else:
        with pytest.raises(GoogleUnavailable):executor.execute(call)
    assert executor.calls==len(statuses)
    assert sleeps==[2**i+.25 for i in range(len(statuses)-1)]


@pytest.mark.parametrize("status",[429,500,502,503,504])
def test_never_replay_unconfirmed_write(status):
    executor=GoogleExecutor(sleep=lambda _:pytest.fail("write retried"))
    def call():raise HttpFailure(status)
    with pytest.raises(WriteUncertain):executor.execute(call,idempotent=False)
    assert executor.calls==1
