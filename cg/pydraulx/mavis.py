"""
    Low-Level Communication with the Mavis API.
"""

import requests
import json

class Mavis(object):

    session = None
    """The encrypted session cookie identifying this particular Mavis instance."""

    def __init__(self, username, password, host = 'localhost', port = '3000', loginUrl = 'api/users/login'):
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


    def find(self, path, **params):
        """ DEPRECATED -- use `get` instead """
        return self.query('get', path, data = None, **params).json()

    def insert(self, path, data, **params):
        """ DEPRECATED -- use `post` instead """
        return self.query('post', path, data = data, **params).json()

    def update(self, path, data, **params):
        """ DEPRECATED -- use `put` instead """
        return self.query('put', path, data = data, **params).json()

    def action(self, action, path, data):
        """ DEPRECATED """
        if path[0] == '/': path = path[1:]
        return self.query('put', '/action/%s/%s' % (action, path), data = data).json()

    def remove(self, path, **params):
        """ DEPRECATED -- use `delete` instead """
        return self.query('delete', path, data = None, **params)

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

        print url
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
