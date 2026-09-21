import argparse
import json
from app.config import settings
from app.container import Container
from app.models.errors import DomainError


def parser(description):
    return argparse.ArgumentParser(description=description)


def output(result):
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def execute(action):
    try:
        result = action()
        output(result)
        return 0
    except DomainError as error:
        output({"correcto": False, "mensaje": str(error)})
        return 1
    except Exception as error:
        output({"correcto": False, "mensaje": "La operación no pudo completarse.", "tipo": type(error).__name__})
        return 1


def container(*, writes=False):
    config = settings()
    # Administrative --execute --confirm flags authorize only this invocation.
    config["GOOGLE_WRITES_ENABLED"] = writes
    return Container(config)
