#!/usr/bin/env python

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


from .custom_runtime import CustomRuntime


# We'll be called by the AWS Custom Runtime agent
if __name__ == "__main__":
    new_runtime = CustomRuntime()

    # Loop infinitely to keep processing events
    while 1:
        new_runtime.process_next_event()
