import os
import requests
import tornado.ioloop
import tornado.web
from urlparse import urljoin

port = os.environ.get("PORT", 5000)
root = os.path.dirname(os.path.abspath(__file__))
api = 'http://104.197.142.168:8080/apps/'

class Redirector(tornado.web.RequestHandler):
    """
    Redirect calls to the Binder API depending on status
    """
    def get(self, app_id):

        baseurl = self.request.protocol + "://" + self.request.host

        r = requests.get(urljoin(api, app_id, '/status'))

        if r.status_code == 404:
            self.redirect(baseurl + '/status/missing.html')
        
        if r.status_code == 200:
            blob = r.json()
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