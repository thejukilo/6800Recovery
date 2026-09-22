from aiohttp import web

from rlx_osal.osal import OSAL
from rlx_osal.errors import OSALError
from .log import logger
from .app_api import app
from .osal.date_and_time import dt_info


@app.http_post("/api/system/settings/date-time")
@app.authenticated
async def setDateTime(request) -> web.Response:
    data = await request.json()
    hours = data.get("hours", None)
    minutes = data.get("minutes", None)
    seconds = data.get("seconds", None)
    day = data.get("day", None)
    month = data.get("month", None)
    year = data.get("year", None)
    logger.info(
        f"Executing OSAL().SetDateTime({hours}, {minutes}, {seconds}, {day}, {month}, {year})"
    )
    try:
        OSAL().SetDateTime(hours, minutes, seconds, day, month, year)
    except OSALError as err:
        logger.error(err)
        return web.Response(
            text="Internal Error: could not set time and date", status=400
        )
    return web.Response()


@app.http_get("/api/system/settings/date-time")
@app.authenticated
async def getDateTime(request) -> web.Response:
    logger.info("Getting date and time info")
    time_and_date_info = dt_info()
    if time_and_date_info:
        # {
        #     "year": response.year,
        #     "month": response.month,
        #     "day": response.day,
        #     "hours": response.hours,
        #     "minutes": response.minutes,
        #     "seconds": response.seconds,
        #     "tz_offset": response.tz_offset,
        #     "tz_name": response.tz_name,
        #     "tz_code": response.tz_code,
        # }
        return web.json_response(time_and_date_info.to_dict())
    return web.Response(text="Internal Error", status=500)
