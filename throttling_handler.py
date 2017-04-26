import time
import urllib2


class ThrottlingHandler(urllib2.BaseHandler):
    """A throttling handler which ensures that requests to a given host
    are always spaced out by at least a certain number of (floating point)
    seconds.
    """

    def __init__(self, throttle_seconds=1.0):
        self._throttleSeconds = throttle_seconds
        self._requestTimeDict = dict()

    def default_open(self, request):
        host_name = request.get_host()
        last_request_time = self._requestTimeDict.get(host_name, 0)
        time_since_last = time.time() - last_request_time

        if time_since_last < self._throttleSeconds:
            time.sleep(self._throttleSeconds - time_since_last)
        self._requestTimeDict[host_name] = time.time()


