import requests
import json
import imp
try:
    imp.find_module('zmq') # check if zmq library is available
    import zmq
    found = True
except ImportError:
    found = False

class Mavis:
    base_url = 'http://localhost:3000'

    def getEntity(self, entityId):
        try:
            response = self._http_get(self.base_url + '/api/Entities/' + str(entityId) + '?filter={"include":"publishes"}' )
        except Exception as e:
            print e
            return None

        return response.json()

    def getPlate(self, id):
        return requests.get('http://localhost:3000/api/Entities/' + str(id), self._get_token() ).json()

    def getProject(self, id):
    	print "  | mavis.getProject()";
    	print "  | \\";
    	x = '{"where": {"templateType":"project", "name":"'+id+'"}}';
    	try:
            response = self._http_get(self.base_url + '/api/Entities?filter=' + x )
        except Exception as e:
            print e
            return None

        return response.json()
    def createActiviy(self, _json):
        # TODO: implement http post to activity
        return






    def __init__(self, token, debug=True):
        self._token = token
        # if found:
        #     print "Detected zmq library"
        #     print zmq.pyzmq_version()

        # if you need to print some logs, pass second paramater as True
        self._isDebug = debug

    def _get_token(self):

        return { 'access_token': self._token }

    def _http_get(self, url):
        """Perform http get request

        If request is bad (a 4XX client error or 5XX server error response),
        we raise exception
        """

        r = requests.get(url, self._get_token())

        if self._isDebug:
            print "  | | Http request url: {}".format(r.url)
            print "  | | Http request status: {}".format(r.status_code)

        if r.status_code != 200:
            r.raise_for_status()

        return r

    def _http_post(self, url, data):
        """Perform http post request
        """
        return

    def _http_put(self, url, data):
        """Perform http put request
        """
        return

    def _http_delete(self, url):
        """Perform http delete request
        """
        return








# import unittest

# class MavisTests(unittest.TestCase):
#     def testOne(self):
#         self.failUnless(True)

#     def testTwo(self):
#         self.failIf(False)


def main():
    # unittest.main()

    conn = Mavis('1XV6iI6zXMM9xNl3hGBHGIJGdpytyrywyny3n86DZhRIrrUns9OkXBXEkFwJtF8C')
    data = conn.getEntity(1)
    # print data


if __name__ == '__main__':
    main()

