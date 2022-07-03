#!/usr/bin/env python
# -*- coding: utf8 -*-

""" Static file server web module for x/84 bbs. """

import os
from utils.settings import ApplicationSettings

class Favicon(object):
    """Dummy class for preventing 404 of /favicon.ico
    """

    def GET(self):
        """ GET request callback (does nothing). """
        pass

def web_module():
    """Expose our REST API. Run only once on server startup.
    """

    # determine document root for web server
    static_root = (ApplicationSettings.get_ini('web', 'document_root')
                   or os.path.join(ApplicationSettings.get_ini('system', 'scriptpath',
                   split=True)[0], 'www-static'))
    Favicon.static_root = static_root

    return {
        'urls': ('/favicon.ico', 'favicon'),
        'funcs': {
            'favicon': Favicon
        }
    }
