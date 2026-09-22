from aiohttp_session import get_session
import asyncio
import json

from .app_api import app


@app.websocket_connect()
async def websocket_connected(ws):
    ws.shell_queue = asyncio.Queue()
    ws.log_queue = asyncio.Queue()
    # notify client of state 'connected'
    await ws.send_str(json.dumps({"subject": "websocket", "event": "connected"}))


@app.websocket_message("/api/websocket", authenticated=False)
async def websocket_message(ws, data):
    session = await get_session(ws.cirrina.request)
    if session.new:
        app.logger.warning("Ignoring incoming message from unauthenticated user")
        return

    msg = json.loads(data)

    if msg.get("command", "") == "startlogs":
        loop = asyncio.get_event_loop()

        async def worker():
            app.logger.debug("ws: log worker started")

            await ws.send_str(json.dumps({"subject": "log", "event": "logstart"}))

            while True:
                item = await ws.log_queue.get()

                if item is None or len(item) != 2:
                    app.logger.warning("Received invalid log entry")
                    break

                logtype, logs = item

                if "@@EOL@@" in logs:  # FIXME: use a logtype as EOL
                    app.logger.debug("ws: end of logs: EOL")
                    break

                if logtype == 0:
                    lt = "syslog"
                elif logtype == 1:
                    lt = "file"
                elif logtype == 3:
                    lt = "ssh"
                else:  # FIXME: add other types
                    lt = "unknown"

                await ws.send_str(
                    json.dumps({"subject": "log", "event": lt, "data": logs})
                )

            await ws.send_str(json.dumps({"subject": "log", "event": "logend"}))
            app.osal.StopSystemLogs(topic)
            app.osal.unsubscribe_client_events(topic)
            app.logger.debug("ws: log worker done")

        asyncio.ensure_future(worker())

        def callback(msg):
            # FIXME: check if logEntries exists
            loop.call_soon_threadsafe(
                ws.log_queue.put_nowait, (msg.logType, list(msg.logEntries))
            )

        ret = app.osal.GetClientEventChannel()
        topic = ret.response.topic
        app.osal.subscribe_client_events(topic, callback)
        msg_filter = ",".join(msg.get("filter", ""))
        app.osal.StartSystemLogs(
            topic,
            msg_filter,
            msg.get("lines", 200),
            msg.get("priority", -1),
            msg.get("fromTime", 0),
            msg.get("toTime", 0),
        )

    elif msg.get("command", "") == "startshell":
        if "web-shell" not in app.get_capabilities():
            return

        loop = asyncio.get_event_loop()

        async def worker():
            app.logger.debug("ws: shell worker started")

            while True:
                data = await ws.shell_queue.get()

                if data is None:
                    break

                await ws.send_str(
                    json.dumps({"subject": "shell", "event": "data", "data": data})
                )

            await ws.send_str(json.dumps({"subject": "shell", "event": "shellend"}))

            app.osal.StopShell(ws.rlx_event_topic)
            app.osal.unsubscribe_client_events(ws.rlx_event_topic)
            app.logger.debug("ws: shell worker done")

        asyncio.ensure_future(worker())

        def callback(msg):
            loop.call_soon_threadsafe(ws.shell_queue.put_nowait, msg.data)

        ret = app.osal.GetClientEventChannel()
        ws.rlx_event_topic = ret.response.topic
        app.osal.subscribe_client_events(ws.rlx_event_topic, callback)
        app.osal.StartShell(
            ws.rlx_event_topic, msg.get("cols", 75), msg.get("rows", 24)
        )

    elif msg.get("command", "") == "shellkey":
        if "web-shell" not in app.get_capabilities():
            return
        app.osal.SendShell(ws.rlx_event_topic, msg.get("key"))

    elif msg.get("command", "") == "stopshell":
        if "web-shell" not in app.get_capabilities():
            return
        await ws.shell_queue.put(None)

    elif msg.get("command", "") == "resizeshell":
        if "web-shell" not in app.get_capabilities():
            return
        app.osal.ResizeShell(ws.rlx_event_topic, msg.get("cols"), msg.get("rows"))


@app.websocket_disconnect()
async def websocket_closed(ws):
    await ws.log_queue.put(None)
    await ws.shell_queue.put(None)
