"""
Command line tool for bulk exporting a range of TCX files from Polar Flow.

Usage is as follows:

    python polarflowexport.py <username> <password> <start_date> \
                <end_date> <output_dir>

The start_date and end_date parameters are ISO-8601 date strings (i.e.
year-month-day). An example invocation is as follows:

    python polarflowexport.py me@me.com mypassword 2015-08-01 2015-08-30 \
                        /tmp/tcxfiles

Licensed under the Apache Software License v2, see:
    http://www.apache.org/licenses/LICENSE-2.0
"""

import contextlib
import cookielib
import json
import logging
import os
import sys
import urllib
import urllib2
import dateutil.parser
from tcxfile import TcxFile
from throttling_handler import ThrottlingHandler


class PolarFlowExporter(object):

    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._logger = logging.getLogger(self.__class__.__name__)

        self._url_opener = urllib2.build_opener(
                        ThrottlingHandler(0.5),
                        urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
        self._url_opener.addheaders = [('User-Agent', 'https://github.com/gabrielreid/polar-flow-export')]
        self._logged_in = False
        self.failed_downloads = []

    def _execute_request(self, path, post_params=None):
        data = ""
        url = "https://flow.polar.com%s" % path
        self._logger.debug("Requesting '%s'" % url)

        if post_params is not None:
            post_data = urllib.urlencode(post_params)
        else:
            post_data = None

        try:
            with contextlib.closing(urllib.urlopen(url)) as x:
                response = self._url_opener.open(url, post_data)
                data = response.read()
        except Exception, e:
            self._logger.error("Error fetching %s: %s" % (url, e))
            if e.code == 404 or e.code == 400:
                self._handle_http_errors(e, url)
                return None
            else:
                raise Exception(e)
        else:
            return data

    def _handle_http_errors(self, ex, url):
        self.failed_downloads.append(url)
        self._logger.error("HTTPError %s" % ex.message)

    def _login(self):
        self._logger.info("Logging in user %s", self._username)
        self._execute_request('/')  # Start a new session
        self._execute_request('/login', 
            dict(returnUrl='https://flow.polar.com/', email=self._username, password=self._password))
        self._logged_in = True 
        self._logger.info("Successfully logged in")

    def get_tcx_files(self, from_date_str, to_date_str):
        """Returns an iterator of TcxFile objects.
        @param from_date_str an ISO-8601 date string
        @param to_date_str an ISO-8601 date string
        """
        self._logger.info("Fetching TCX files from %s to %s", from_date_str, to_date_str)
        if not self._logged_in:
            self._login()

        from_date = dateutil.parser.parse(from_date_str)
        to_date = dateutil.parser.parse(to_date_str)
        from_spec = "%s.%s.%s" % (from_date.day, from_date.month, from_date.year)
        to_spec = "%s.%s.%s" % (to_date.day, to_date.month, to_date.year)

        path = "/training/getCalendarEvents?start=%s&end=%s" % (from_spec, to_spec)
        activity_refs = json.loads(self._execute_request(path))

        def get_tcx_file(activity_ref):
            url = activity_ref['url']
            if "fitness" in url or "orthostatic" in url:
                print("will not download %s" % url)
                self.failed_downloads.append(url)
                return None
            else:
                self._logger.info("Retrieving workout from %s" % activity_ref['url'])
                return TcxFile(activity_ref['listItemId'],
                               activity_ref['datetime'],
                               self._execute_request("%s/export/tcx/false" % url))

        tcx_files = []
        for activity_ref in activity_refs:
            tcx = get_tcx_file(activity_ref)
            if tcx:
                write_file(tcx)
                tcx_files.append(tcx)


def write_file(tcx_file):
    filename = "%s_%s.tcx" % (tcx_file.date_str.replace(':', '_'), tcx_file.workout_id)
    with open(os.path.join(output_dir, filename), 'wb') as f:
        f.write(tcx_file.content)
    print("Wrote file %s" % filename)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        (username, password, from_date_str, to_date_str, output_dir) = sys.argv[1:]
    except ValueError:
        sys.stderr.write(("Usage: %s <username> <password> <from_date> "
            "<to_date> <output_dir>\n") % sys.argv[0])
        sys.exit(1)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    exporter = PolarFlowExporter(username, password)
    exporter.get_tcx_files(from_date_str, to_date_str)


    print("Export complete")
    print ("These activities were not downloaded:")

    for d in exporter.failed_downloads:
        print(d)
