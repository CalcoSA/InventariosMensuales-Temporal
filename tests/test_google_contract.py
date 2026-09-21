import json
from types import SimpleNamespace
import pytest
from googleapiclient.discovery import build
from googleapiclient.http import HttpMockSequence
from app.services.google_sheets import GoogleSheetsService
from app.services.google_drive import GoogleDriveService
from app.services.retry import GoogleExecutor
from app.models.errors import ConfigurationError


class CapturingHTTP:
    def __init__(self,responses):
        self.responses=iter(responses);self.requests=[]
    def request(self,uri,method="GET",body=None,headers=None,**kwargs):
        import httplib2
        self.requests.append((uri,method,body))
        status,payload=next(self.responses)
        return httplib2.Response({"status":str(status),"content-type":"application/json"}),json.dumps(payload).encode()
    def close(self):pass


class FakeAuth:
    def __init__(self,http):self.http=http
    def client(self,api,version):return build(api,version,http=self.http,cache_discovery=False,static_discovery=True)


def test_actual_sheets_request_builder_and_batched_write():
    http=CapturingHTTP([(200,{"sheets":[]}), (200,{"replies":[]})])
    service=GoogleSheetsService(FakeAuth(http),GoogleExecutor(),writes=True)
    assert service.read_book("spreadsheet")==[]
    service.batch_update("spreadsheet",[{"updateCells":{"start":{"sheetId":1},"rows":[],"fields":"userEnteredValue"}}])
    from urllib.parse import urlsplit,parse_qs
    params=parse_qs(urlsplit(http.requests[0][0]).query)
    fields=params["fields"][0]
    depth=0
    for char in fields:
        depth+=(char=="(")-(char==")")
        assert depth>=0,fields
    assert depth==0,fields
    assert http.requests[0][1]=="GET"
    assert http.requests[1][1]=="POST"
    assert len(json.loads(http.requests[1][2])["requests"])==1


def test_drive_pagination_and_query_escaping():
    http=CapturingHTTP([(200,{"files":[{"id":"1"}],"nextPageToken":"page2"}),(200,{"files":[{"id":"2"}]})])
    service=GoogleDriveService(FakeAuth(http),GoogleExecutor())
    assert service.list("folder",name="O'Brien")==[{"id":"1"},{"id":"2"}]
    from urllib.parse import parse_qs,urlsplit
    assert "O\\'Brien" in parse_qs(urlsplit(http.requests[0][0]).query)["q"][0]
    assert parse_qs(urlsplit(http.requests[1][0]).query)["pageToken"]==["page2"]
    with pytest.raises(ConfigurationError):service.create_folder("parent","name")


def test_read_429s_share_one_retry_policy():
    http=CapturingHTTP([(429,{"error":{"message":"quota"}}),(429,{"error":{"message":"quota"}}),(200,{"sheets":[]})])
    sleeps=[]
    executor=GoogleExecutor(sleep=sleeps.append,jitter=lambda:0)
    assert GoogleSheetsService(FakeAuth(http),executor).read_book("x")==[]
    assert len(http.requests)==3 and sleeps==[1,2]
