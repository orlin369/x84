#!/usr/bin/env python
# -*- coding: utf8 -*-

""" web server for x/84. """

import sys
import os
import threading
import traceback
import logging
import importlib

from utils.settings import ApplicationSettings

import web
from web.wsgiserver import CherryPyWSGIServer
from cheroot.ssl.pyopenssl import pyOpenSSLAdapter
from OpenSSL import SSL

def _get_fp(section_key, optional=False):
    """ Return filepath of [web] option by ``section_key``. """

    value = ApplicationSettings.get_ini(section='web', key=section_key) or None

    if value:
        value = os.path.expanduser(value)

    elif optional:
        return None

    assert value is not None and os.path.isfile(value), (
        'Configuration section [web], key `{section_key}`, '
        'must {optional_exist}identify a path to an '
        'SSL {section_key} file. '
        '(value is {value})'.format(
            section_key=section_key,
            optional_exist=not optional and 'exist and ' or '',
            value=value))
 
    return value

def get_urls_funcs(web_modules_names):
    """ Get url function mapping for the given web modules. """
    log = logging.getLogger(__name__)

    # list of url's to route to each WEB module api; defaults to route /favicon.ico
    # to a non-op to avoid 404 errors.
    # See: http://webpy.org/docs/0.3/api#web.application
    urls = ()
    funcs = globals()

    for web_module_name in web_modules_names:
        web_module = None

        module_path = "web_modules.{}.{}".format(web_module_name, web_module_name)
        web_module = importlib.import_module(module_path)

        # first, check in system PATH (includes script_path)
        if web_module is None:
            raise ImportError("{}".format(module_path))

        api = web_module.web_module()

        for key in api['funcs']:
            funcs[key] = api['funcs'][key]

        # use zip to transform (1,2,3,4,5,6,7,8) =>
        # [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8)]
        # then, use slice to 'step 2' =>
        # [(1, 2), (3, 4), (5, 6), (7, 8)]
        for (url, f_key) in zip(api['urls'], api['urls'][1:]):
            if f_key not in funcs:
                log.error('web module {web_module} provided url {url_tuple} without matching function (available: {f_avail})'
                          .format(web_module=web_module, url_tuple=(url, f_key,), f_avail=funcs.keys()))

            else:
                log.debug('add url {} => {}'.format(url, funcs[f_key].__name__))

        urls += api['urls']

    return urls, funcs

def server(urls, funcs):
    """ Main server thread for running the web server """

    log = logging.getLogger(__name__)

    cert, key, chain = (_get_fp('cert'),
                        _get_fp('key'),
                        _get_fp('chain', optional=True))

    addr = ApplicationSettings.get_ini(section='web',
                   key='addr'
                   ) or '0.0.0.0'

    port = ApplicationSettings.get_ini(section='web',
                   key='port',
                   getter='getint'
                   ) or 8443

    # List of ciphers made available, composed by haliphax without reference,
    # but apparently to prevent POODLE? This stuff is hard -- the best source
    # would probably be to compare by cloudflare's latest sslconfig file:
    #
    #   https://github.com/cloudflare/sslconfig/blob/master/conf
    #
    cipher_list = (ApplicationSettings.get_ini(section='web', key='cipher_list')
                   or ':'.join((
                       'ECDH+AESGCM',
                       'ECDH+AES256',
                       'ECDH+AES128',
                       'ECDH+3DES',
                       'DH+AESGCM',
                       'DH+AES256',
                       'DH+AES',
                       'DH+3DES',
                       'RSA+AESGCM',
                       'RSA+AES',
                       'RSA+3DES',
                       '!aNULL',
                       '!MD5',
                       '!DSS',
                   )))

    CherryPyWSGIServer.ssl_adapter = pyOpenSSLAdapter(cert, key, chain)
    CherryPyWSGIServer.ssl_adapter.context = SSL.Context(SSL.SSLv23_METHOD)
    CherryPyWSGIServer.ssl_adapter.context.set_options(SSL.OP_NO_SSLv3)

    try:
        CherryPyWSGIServer.ssl_adapter.context.use_certificate_file(cert)

    except Exception:
        # wrap exception to contain filepath to 'cert' file, which will
        # hopefully help the user better understand what otherwise be very
        # obscure.
        error = ''.join(
            traceback.format_exception_only(
                sys.exc_info()[0],
                sys.exc_info()[1])).rstrip()

        raise ValueError('Exception loading ssl certificate file {}: {}'.format(cert, error))

    try:
        CherryPyWSGIServer.ssl_adapter.context.use_privatekey_file(key)

    except Exception:
        # also wrap exception to contain filepath to 'key' file.
        error = ''.join(
            traceback.format_exception_only(
                sys.exc_info()[0],
                sys.exc_info()[1])).rstrip()

        raise ValueError('Exception loading ssl key file {}: \'{}\''.format(key, error))

    if chain is not None:
        (CherryPyWSGIServer.ssl_adapter.context
         .use_certificate_chain_file(chain))

    CherryPyWSGIServer.ssl_adapter.context.set_cipher_list(cipher_list)

    # TODO: It is stops here. 03.07.2022g. FIX IT!
    app = web.application(urls, funcs)

    web.config.debug = False

    log.info('https listening on {addr}:{port}/tcp'.format(addr=addr, port=port))

    # Runs CherryPy WSGI server hosting WSGI app.wsgifunc().
    web.httpserver.runsimple(app.wsgifunc(), (addr, port))  # blocking


def main(background_daemon=True):
    """
    Entry point to configure and begin web server.

    Called by x84/engine.py, function main() as unmanaged thread.

    :param bool background_daemon: When True (default), this function returns
       and web modules are served in an unmanaged, background (daemon) thread.
       Otherwise, function call to ``main()`` is blocking.
    :rtype: None
    """

    log = logging.getLogger(__name__)

    script_path = ApplicationSettings.get_ini(section='system', key='scriptpath', split=True)

    # ensure the script_path is in os environment PATH for web_module lookup.
    for directory in script_path:
        sys.path.insert(0, os.path.expanduser(directory))

    web_modules = ApplicationSettings.get_ini(section='web', key='modules', split=True)

    if not web_modules:
        log.error("web server enabled, but no `modules' "
                  "defined in section [web]")
        return

    log.debug('Ready web modules: {}'.format(web_modules))
    urls, funcs = get_urls_funcs(web_modules)

    if background_daemon:
        t = threading.Thread(target=server, args=(urls, funcs,))
        t.daemon = True
        t.start()
    else:
        server(urls=urls, funcs=funcs)
