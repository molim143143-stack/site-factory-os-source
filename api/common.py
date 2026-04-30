from fastapi import Request


def trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", None)


def request_id_from(data: dict) -> str:
    return data.get("request_id") or ""
