import time
import urllib2


class ThrottlingHandler(urllib2.BaseHandler):
    """A throttling handler which ensures that requests to a given host
    are always spaced out by at least a certain number of (floating point)
    seconds.
    """

    def __init__(self, throttleSeconds=1.0):
        self._throttleSeconds = throttleSeconds
        self._requestTimeDict = dict()

    def default_open(self, request):
        hostName = request.get_host()
        lastRequestTime = self._requestTimeDict.get(hostName, 0)
        timeSinceLast = time.time() - lastRequestTime

        if timeSinceLast < self._throttleSeconds:
            time.sleep(self._throttleSeconds - timeSinceLast)
        self._requestTimeDict[hostName] = time.time()


