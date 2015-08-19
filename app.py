import os
import requests
import tornado.ioloop
import tornado.web
from tornado.options import define, options

from urlparse import urljoin

define("api", default="104.197.142.168", help="IP address for binder API endpoint")

port = os.environ.get("PORT", 5000)
root = os.path.dirname(os.path.abspath(__file__))

class Redirector(tornado.web.RequestHandler):
    """
    Redirect calls to the Binder API depending on status
    """
    def get(self, app_id):

        baseurl = self.request.protocol + "://" + self.request.host
        endpoint = 'http://' + options.api + ':8080/apps/'

        r = requests.get(urljoin(endpoint, app_id + '/status'))

        print(r.status_code)

        if r.status_code == 404:
            self.redirect(baseurl + '/status/missing.html')
        
        if r.status_code == 200:
            blob = r.json()
            print(blob)
            if 'build_status' in blob:
                status = blob['build_status']
                if status == 'failed':
                    self.redirect(baseurl + '/status/failed.html')
                if status == 'building':
                    self.redirect(baseurl + '/status/building.html')
            elif 'redirect_url' in blob:
                url = blob['redirect_url']
                self.redirect(url)
            else:
                self.redirect(baseurl + '/status/unknown.html')

class CustomStatic(tornado.web.StaticFileHandler):
    """
    Modified static handler to serve a custom 404
    """
    def write_error(self, status_code, **kwargs):
        baseurl = self.request.protocol + "://" + self.request.host
        self.redirect(baseurl + '/status/404.html')


application = tornado.web.Application([
    (r"/apps/(?P<app_id>.*)", Redirector),
    (r"/(.*)", CustomStatic, {'path': root + "/static/", "default_filename": "index.html"})
])

if __name__ == "__main__":
    application.listen(port)
    tornado.ioloop.IOLoop.current().start()