from typing import Dict
from dataclasses import dataclass

from rlx_web.log import logger
from rlx_osal.osal import OSAL
from rlx_osal.errors import (
    OSALCallError,
    UnknownOSALMethodError,
    OSALError,
    OSALNoneError,
    OSALUnknownRequestError,
    OSALBusyError,
    OSALProcessingError,
    OSALNoBackgroundError,
    OSALParameterError,
)


@dataclass
class Keyboard:
    code: str = ""
    layout: str = ""


class KeyboardLayouts:
    @property
    def layouts(self) -> Dict[str, str]:
        layout_dict = {}
        try:
            ret = OSAL().GetKeyboardLayoutList()
            keyboards = list(ret.response.keyboards)
            for keyboard in keyboards:
                layout_dict[keyboard.code] = keyboard.layout
        except (
            AttributeError,
            OSALCallError,
            UnknownOSALMethodError,
            OSALError,
            OSALNoneError,
            OSALUnknownRequestError,
            OSALBusyError,
            OSALNoBackgroundError,
            OSALProcessingError,
            OSALParameterError,
        ) as err:
            logger.error(err)
        return layout_dict

    @property
    def current_layout(self) -> Keyboard:
        code = ""
        try:
            ret = OSAL().GetCurrentKeyboardCode()
            code = ret.response.code
        except (
            AttributeError,
            OSALCallError,
            UnknownOSALMethodError,
            OSALError,
            OSALNoneError,
            OSALUnknownRequestError,
            OSALBusyError,
            OSALNoBackgroundError,
            OSALProcessingError,
            OSALParameterError,
        ) as err:
            logger.exception(err)
        current_layout = Keyboard(code, layout=self.layouts.get(code, ""))
        return current_layout
