from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
import subprocess
import sys
import pytest
from app.services.locking import SpreadsheetLocks
from app.models.errors import GoogleUnavailable

ROOT=Path(__file__).resolve().parent.parent


def test_app_creation_never_starts_a_server(tmp_path, monkeypatch):
    import socket
    from flask import Flask
    from app import create_app
    from tests.conftest import make_container
    monkeypatch.setattr(Flask,"run",lambda *a,**kw:pytest.fail("Automatic server startup"))
    monkeypatch.setattr(socket.socket,"bind",lambda *a,**kw:pytest.fail("Listening socket created"))
    app=create_app({"TESTING":True},container=make_container(tmp_path))
    assert app.test_client().get("/").status_code==200


@pytest.mark.parametrize("script",["generate_monthly_bases.py","prepare_monthly_bases.py","cleanup_monthly_counts.py"])
def test_admin_execute_requires_confirmation(script):
    result=subprocess.run([sys.executable,"-B",str(ROOT/"scripts"/script),"--execute"],capture_output=True,text=True)
    assert result.returncode==2
    assert "--confirm" in result.stderr


def test_locks_are_per_spreadsheet_and_release_on_error(tmp_path):
    locks=SpreadsheetLocks(tmp_path,timeout=.1)
    with locks.hold("one"):
        with locks.hold("two"):
            pass
        with pytest.raises(GoogleUnavailable):
            with locks.hold("one"):pass
    with locks.hold("one"):pass


def test_locks_shared_between_processes(tmp_path):
    locks=SpreadsheetLocks(tmp_path,timeout=3)
    code=(
        "from pathlib import Path; from app.services.locking import SpreadsheetLocks; "
        "from app.models.errors import GoogleUnavailable; import sys\n"
        "try:\n"
        " with SpreadsheetLocks(Path(sys.argv[1]), timeout=.1).hold('pdv'): sys.exit(5)\n"
        "except GoogleUnavailable: sys.exit(0)\n"
    )
    with locks.hold("pdv"):
        child=subprocess.run([sys.executable,"-B","-c",code,str(tmp_path)],cwd=ROOT,capture_output=True,text=True)
    assert child.returncode==0,child.stderr
