
"""
Copyright (C) Refinery Labs Inc. - All Rights Reserved

NOTICE: All information contained herein is, and remains
the property of Refinery Labs Inc. and its suppliers,
if any. The intellectual and technical concepts contained
herein are proprietary to Refinery Labs Inc.
and its suppliers and may be covered by U.S. and Foreign Patents,
patents in process, and are protected by trade secret or copyright law.
Dissemination of this information or reproduction of this material
is strictly forbidden unless prior written permission is obtained
from Refinery Labs Inc.
"""

import datetime
import time


"""
{
	"action_name": {
		"start": time.time(),
		"end": time.time(),
		"total": 0,
	}
}
"""
_CLOCK_TIMES = {}


def _start_clock(action_name):
    return
    global _CLOCK_TIMES
    _CLOCK_TIMES[action_name] = {
        "start": datetime.datetime.now(),
        "end": 0,
        "total": 0,
    }


def _stop_clock(action_name):
    return
    global _CLOCK_TIMES
    _CLOCK_TIMES[action_name]["end"] = datetime.datetime.now()
    _CLOCK_TIMES[action_name]["total"] = (
        (
            time.mktime(_CLOCK_TIMES[action_name]["end"].timetuple(
            ))*1e3 + _CLOCK_TIMES[action_name]["end"].microsecond/1e3
        ) - (
            time.mktime(_CLOCK_TIMES[action_name]["start"].timetuple(
            ))*1e3 + _CLOCK_TIMES[action_name]["start"].microsecond/1e3
        )
    )
    print("[ INFO ] The action '" + action_name + "' took " +
          str((_CLOCK_TIMES[action_name]["total"] * 0.001)) + " second(s).")
