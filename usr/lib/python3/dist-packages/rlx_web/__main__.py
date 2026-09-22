import asyncio

import click
from google.protobuf import json_format
from launchy import Launchy

from rlx_web.app_api import app, offlineLaunchCode, sendevent
from rlx_web.log import logger

loop = asyncio.get_event_loop()


def event_handler(rootevent):
    eventname = rootevent.data.type_url.split("/")[-1]
    # TODO: TPQ - propagate the outcome and the jobid to the websocket
    if eventname:
        event = app.osal.descriptors[eventname]()
        event.ParseFromString(rootevent.data.value)
        outcome = rootevent.outcome
        errorMessage = rootevent.errorMessage
        jobID = rootevent.jobID

        data = json_format.MessageToDict(event)
        data["outcome"] = outcome
        data["errorMessage"] = errorMessage
        data["jobID"] = jobID
        asyncio.run_coroutine_threadsafe(
            sendevent(type(event).__name__, data), loop=loop
        )


@click.command()
@click.option(
    "--host", default="localhost", help="Hostname, examples: 'localhost' or '0.0.0.0'"
)
@click.option("--port", default=8888, help="Listen port")
@click.option("--debug/--no-debug", default=False, help="Enable debug")
def mainloop(host, port, debug):
    app.osal.subscribe_events(event_handler)
    app.osal.enable_client_events()
    asyncio.run_coroutine_threadsafe(offlineLaunchCode(), loop=loop)
    app.run(host, port, debug=debug, logger=logger)


Launchy.attach_loop(loop)
loop.run_until_complete(mainloop())
asyncio.run_coroutine_threadsafe(Launchy.stop(), loop)
