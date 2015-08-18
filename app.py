import os
import requests
import tornado.ioloop
import tornado.web
from tornado.options import options, define
from urlparse import urljoin


define("host", default="localhost", help="app host", type=str)
define("port", default=8888, help="app port", type=int)

root = os.path.dirname(os.path.abspath(__file__))
api = 'http://104.197.142.168:8080/apps/'

class Redirector(tornado.web.RequestHandler):
    def get(self, app_id):

        baseurl = 'http://' + options.host + ':' + str(options.port)

        r = requests.get(urljoin(api, app_id))

        if r.status_code == 404:
            self.redirect(baseurl + '/status/404.html')
        
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
        
application = tornado.web.Application([
    (r"/apps/(?P<app_id>.*)", Redirector),
    (r"/(.*)", tornado.web.StaticFileHandler, {'path': root + "/static/", "default_filename": "index.html"})
])

if __name__ == "__main__":
    options.parse_command_line()
    application.listen(options.port)
    tornado.ioloop.IOLoop.current().start()