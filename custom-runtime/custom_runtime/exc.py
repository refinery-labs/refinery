
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


class AlreadyInvokedException(Exception):
    def __init__(self, message="This function has already been invoked!"):
        # Call the base class constructor with the parameters it needs
        super(AlreadyInvokedException, self).__init__(message)


class InvokeQueueEmptyException(Exception):
    def __init__(self, message="We've exhausted all of the invocations we have to do!"):
        # Call the base class constructor with the parameters it needs
        super(InvokeQueueEmptyException, self).__init__(message)
