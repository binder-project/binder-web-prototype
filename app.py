import os
import requests
import logging
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
    def get(self, org, repo, location=None):

        # strip trailing /
        if repo[-1] == '/':
            repo = repo[:-1]

        # get locations
        app_id = org + "/" + repo
        baseurl = self.request.protocol + "://" + self.request.host
        endpoint = 'http://' + options.api + ':8080/apps/'
        
        try:
            r = requests.get(urljoin(endpoint, app_id + '/status'))

            if r.status_code == 404:
                logging.info('cannot get status')
                logging.info('sending missing message')
                self.redirect(baseurl + '/status/missing.html')
            
            if r.status_code == 200:
                logging.info('status retrieved')
                blob = r.json()        
                if 'build_status' in blob:
                    status = blob['build_status']
                    if status == 'failed':
                        logging.debug('sending failed message')
                        self.redirect(baseurl + '/status/failed.html')
                    if status == 'building':
                        logging.debug('sending build message')
                        self.render('static/status/building.html')
                    if status == 'completed':
                        # check for capacity
                        r = requests.get(url='http://' + options.api + ':8080/capacity')
                        check = r.json()
                        if check['running'] > 0.8 * check['capacity']:
                            self.render('static/status/capacity.html')
                        else:
                            try:
                                r = requests.get(url=urljoin(endpoint, app_id), timeout=(10.0, 10.0))
                                redirectblob = r.json()
                                if 'redirect_url' in redirectblob:
                                    url = redirectblob['redirect_url']
                                    if location is not None and location != '':
                                        logging.debug('redirecting to: %s' % url + "/notebooks/" + location)
                                        self.redirect(url + "/notebooks/" + location)
                                    else:
                                        logging.debug('redirecting to: %s' % url)
                                        self.redirect(url)
                                else:
                                    self.redirect(baseurl + '/status/unknown.html')
                            except Exception as e:
                                self.timeout_handler(e)

                else:
                    self.redirect(baseurl + '/status/unknown.html')

        except Exception as e:
            self.error_handler(e)

    def timeout_handler(self, e):
        """
        Handler that checks for timeouts
        (useful if we expect timeouts at particular stages)
        """
        baseurl = self.request.protocol + "://" + self.request.host
        logging.error(e)
        if isinstance(e, (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout)):
            logging.info('sending at capacity message')
            self.render('static/status/capacity.html')
        else:
            logging.info('sending unknown error message')
            self.redirect(baseurl + '/status/unknown.html')

    def error_handler(self, e):
        """
        Handler for generic errors
        """
        baseurl = self.request.protocol + "://" + self.request.host
        logging.error(e)
        self.redirect(baseurl + '/status/unknown.html')

class CustomStatic(tornado.web.StaticFileHandler):
    """
    Modified static handler to serve a custom 404
    """
    def write_error(self, status_code, **kwargs):
        baseurl = self.request.protocol + "://" + self.request.host
        self.redirect(baseurl + '/status/404.html')

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static")
}

application = tornado.web.Application([
    (r"/repo/(?P<org>[^\/]+)/(?P<repo>[^\/]+)/(?P<location>.*)", Redirector),
    (r"/repo/(?P<org>[^\/]+)/(?P<repo>[^\/]+)", Redirector),
    (r"/(.*)", CustomStatic, {'path': root + "/static/", "default_filename": "index.html"})
], autoreload=True, **settings)

if __name__ == "__main__":
    tornado.log.enable_pretty_logging()
    application.listen(port)
    for dir, _, files in os.walk('static'):
        [tornado.autoreload.watch(dir + '/' + f) for f in files if not f.startswith('.')]
    tornado.ioloop.IOLoop.current().start()