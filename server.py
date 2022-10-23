import dataclasses
import json
import os
import pathlib
import pprint
from datetime import datetime

import jinja2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

ALL_HTTP_METHODS = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT", "TRACE"]


@dataclasses.dataclass
class RequestInfo:
    """Holder of all the info for a request."""
    timestamp: str
    origin_ip: str
    method: str
    scheme: str
    http_version: str
    path: str
    headers: str
    body: str


class Persistence:
    def __init__(self):
        name = os.environ.get("HTTP_TRYOUT_PERSISTENCE", "http_tryout.history")
        self.persistence_path = pathlib.Path(name)

    def append(self, request_info: RequestInfo):
        """Add a record to the persisted file."""
        record = dataclasses.asdict(request_info)
        with self.persistence_path.open("at", encoding="utf8") as fh:
            fh.write(json.dumps(record) + "\n")

    def __iter__(self):
        with self.persistence_path.open("rt", encoding="utf8") as fh:
            for line in fh:
                data = json.loads(line)
                request_info = RequestInfo(**data)
                yield request_info


app = FastAPI()
persistence = Persistence()

environment = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))
root_template = environment.get_template("home.html")


@app.get("/", response_class=HTMLResponse)
async def root():
    return root_template.render(all_requests=list(persistence))


@app.api_route("/{path:path}", methods=ALL_HTTP_METHODS)
async def extra(path: str, request: Request):
    body = await request.body()
    ri = RequestInfo(
        timestamp=f"{datetime.now():%Y-%m-%d %H:%M:%S}",
        origin_ip=request.client.host,
        method=request.method,
        scheme=request.scope['scheme'].upper(),
        http_version=request.scope['http_version'],
        path="/" + path,
        headers=pprint.pformat(dict(request.headers), width=40),
        body=repr(body)[2:-1],
    )
    persistence.append(ri)
    return JSONResponse(
        content=dict(
            message=f"check your request at server URL: {app.url_path_for('root')}"
            )
        )