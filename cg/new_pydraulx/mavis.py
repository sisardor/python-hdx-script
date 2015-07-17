"""
    Low-Level Communication with the Mavis API.
"""

import requests
import json

class Mavis(object):

    session = None
    """The encrypted session cookie identifying this particular Mavis instance."""

    def __init__(self, username, password, host = 'localhost', port = '3000', loginUrl = 'api/Users/login'):
        """
            Please see the docs concerning Mavis authentication.
        """

        self.host = host
        self.port = port
        self.username = username

        self.query('post', loginUrl, {'password':password, 'username': username})

    def get(self, path, **params):
        """ READ """
        return self.query('get', path, data = None, **params).json()

    def post(self, path, data, **params):
        """ CREATE """
        return self.query('post', path, data = data, **params).json()

    def put(self, path, data, **params):
        """ UPDATE """
        return self.query('put', path, data = data, **params).json()

    def delete(self, path, **params):
        """ DELETE """
        return self.query('delete', path, data = None, **params).json()

    def getEntity(self, entityId):
        query_filter = '?filter[include]=publishes'
        url = '/api/Entities/' + str(entityId) + query_filter
        return self.get(url)

    def getProject(self, projectNameStr):
        query_filter = '?filter[where][templateType]=project'
        query_filter += '&filter[where][name]=' + projectNameStr
        url = '/api/Entities/findOne' + query_filter

        return self.get(url)

    def entityForPath(self, entityPath):
        query_filter = '?filter[where][path]=' + entityPath
        url =   '/api/Entities/findOne' + query_filter

        return self.get(url)

    def query(self, method, path, data = None, **params):
        """
            Perform the Mavis query.
        """

        contentType = 'application/json'

        if isinstance(data, dict) or isinstance(data, list): data = json.dumps(data)
        elif isinstance(data, str): contentType = 'text/plain'
        elif data is not None:
            raise TypeError('Data passed to Mavis must be a dictionary, list '
              'or string [%s given]' % type(data))

        # construct the URL
        if path[0] != '/': path = '/%s' % path
        url = ''.join(['http://', self.host, ':', self.port, path])

        # print url
        try:
            resp = getattr(requests, method)(
                url,
                data            = data,
                params          = params,
                allow_redirects = False,
                cookies         = self.session,
                headers         = {'content-type': contentType}
            )
        except requests.exceptions.ConnectionError:
            raise MavisError('Connection Refused - Mavis may be offline or unreachable.')
        except Exception as e:
            raise MavisError(500, e.args[0])

        if resp.cookies:
            self.session = resp.cookies

        if resp.status_code > 399 and resp.status_code != 404:
            try: message = resp.json()['error']
            except: message = resp.text
            raise MavisError(resp.status_code, message)

        return resp

class MavisError(Exception):
    """Pass through class to easily identify MavisErrors"""

    def __init__(self, code, message = None):
        if isinstance(code, str):
            message = code
            code = 500

        self.errno = code
        Exception.__init__(self, message)




# import unittest

# class MavisTests(unittest.TestCase):
#     def testOne(self):
#         self.failUnless(True)

#     def testTwo(self):
#         self.failIf(False)


def main():
    # unittest.main()
    # return
    conn =  Mavis('trevor', 'password');

    entityId = 21

    # Step 1
    data = conn.getEntity(entityId)
    if 'error' in data:
        print '\n404: NOT FOUND\t Entity#%s\n'%entityId; return


    print 'Entity#%s json:\n%s\n'%(data['id'], data)

    # Step 2
    project = conn.getProject(data['project'])
    print 'Project for Entity#%s:\n%s\n'%(data['id'], project)




if __name__ == '__main__':
    main()

