#!/usr/bin/env python
# -*- coding: utf8 -*-

""" Configuration package x/84. """

from __future__ import print_function
import logging.config
import configparser
import inspect
import getpass
import socket
import os

import warnings

class ApplicationSettings:
    """Application settings.
    """

#region Attributes

    __logger = None
    """Logger
    """    

    __cfg_bbs = None
    """BBS configuration.
    """    

    __instance = None
    """Singelton instance
    """

#endregion

#region Constructor

    def __init__(self, lookup_bbs, lookup_log):
        """Initialize singleton to contain BBS settings.

        Each variable (``lookup_bbs``, ``lookup_log``) is tuple lookup path of
        in-order preferences for .ini files.  If none are found, defaults are
        initialized, and the last item of each tuple is created.

        Args:
            lookup_bbs (tuple): _description_
            lookup_log (tuple): _description_
        """

        self.__logger = logging.getLogger(__name__)

        # exploit last argument, presumed to be within a folder
        # writable by our process, and where the ini is wanted
        # -- engine.py specifys a default of: ~/.x84/somefile.ini
        loaded = False

        cfg_logfile = lookup_log[-1]
        for cfg_logfile in lookup_log:
            cfg_logfile = os.path.expanduser(cfg_logfile)
            # load-only defaults,

            if os.path.exists(cfg_logfile):
                print('Loading: {}'.format((cfg_logfile)))
                logging.config.fileConfig(cfg_logfile)
                loaded = True
                break

        if not loaded:
            cfg_log = self.__init_log_ini()
            dir_name = os.path.dirname(cfg_logfile)

            if not os.path.isdir(dir_name):
                try:
                    os.makedirs(dir_name)

                except OSError as err:
                    self.__logger.warning(err)

            try:
                self.__write_cfg(cfg_log, cfg_logfile)
                self.__logger.info('Saved %s', cfg_logfile)

            except IOError as err:
                self.__logger.error(err)

            logging.config.fileConfig(cfg_logfile)

        loaded = False
        self.__cfg_bbs = configparser.ConfigParser()
        cfg_bbsfile = lookup_bbs[-1]
        for cfg_bbsfile in lookup_bbs:
            cfg_bbsfile = os.path.expanduser(cfg_bbsfile)

            # load defaults,
            if os.path.exists(cfg_bbsfile):
                self.__cfg_bbs.read(cfg_bbsfile)
                self.__logger.info('loaded %s', cfg_bbsfile)
                loaded = True
                break

        if not loaded:
            self.__cfg_bbs = self.__init_bbs_ini()
            dir_name = os.path.dirname(cfg_bbsfile)

            if not os.path.isdir(dir_name):
                try:
                    os.makedirs(dir_name)

                except OSError as err:
                    self.__logger.warning(err)

            try:
                self.__write_cfg(self.__cfg_bbs, cfg_bbsfile)
                self.__logger.info('Saved %s', cfg_bbsfile)

            except IOError as err:
                self.__logger.error(err)

        if ApplicationSettings.__instance is None:
            ApplicationSettings.__instance = self

#endregion

#region Private Methods

    def __write_cfg(self, configuration, file_path):
        """Write Config to file_path.

        Args:
            configuration (Any): Configuration
            file_path (str): File path.
        """

        if not os.path.exists(os.path.dirname(os.path.expanduser(file_path))):
            dir_name = os.path.dirname(os.path.expanduser(file_path))
            print('Creating folder {}'.format(dir_name))
            os.mkdir(dir_name)

        print('Saving {}'.format(file_path))

        configuration.write(open(os.path.expanduser(file_path), 'w'))

    def __init_bbs_ini(self):
        """Returns ConfigParser instance of bbs system defaults.

        Returns:
            configparser.RawConfigParser: Instance of the default settings.
        """

        cfg_bbs = configparser.ConfigParser()

        cfg_bbs.add_section('system')
        cfg_bbs.set('system', 'bbsname', 'x/84')
        cfg_bbs.set('system', 'sysop', '')
        cfg_bbs.set('system', 'software', 'x/84')
        # use module-level 'default' folder
        cfg_bbs.set('system', 'scriptpath', os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, 'default')))
        cfg_bbs.set('system', 'datapath', os.path.expanduser(os.path.join(os.path.join('~', '.x84', 'data'))))
        cfg_bbs.set('system', 'timeout', '1984')

        try:
            # pylint: disable=W0612
            #         Unused variable 'bcrypt'
            import bcrypt  # NOQA

        except ImportError:
            cfg_bbs.set('system', 'password_digest', 'internal')

        else:
            cfg_bbs.set('system', 'password_digest', 'bcrypt')
        cfg_bbs.set('system', 'mail_addr',
                    '%s@%s' % (getpass.getuser(), socket.gethostname()))
        cfg_bbs.set('system', 'mail_smtphost', 'localhost')

        # one *Could* change 'ansi' termcaps to 'ansi-bbs', for SynchTerm,
        # but how do we identify that 'ansi-bbs' TERM is available on this
        # system? hmm .. lets offer the reverse, anything beginning with
        # 'ansi' can changed to any other value; so we could be
        # unidirectional: a value of 'ansi' will translate ansi-bbs -> ansi,
        # and a value of 'ansi-bbs' will translate ansi -> ansi-bbs.
        cfg_bbs.set('system', 'termcap-ansi', 'ansi')
        # change 'unknown' termcaps to 'ansi': for dumb terminals
        cfg_bbs.set('system', 'termcap-unknown', 'ansi')
        # could be information leak to sensitive sysops
        cfg_bbs.set('system', 'show_traceback', 'yes')
        # store passwords in uppercase, facebook and mystic bbs does this ..
        cfg_bbs.set('system', 'pass_ucase', 'no')
        # default encoding for the showart function on UTF-8 capable terminals
        cfg_bbs.set('system', 'art_utf8_codec', 'cp437')

        cfg_bbs.add_section('telnet')
        cfg_bbs.set('telnet', 'enabled', 'yes')
        cfg_bbs.set('telnet', 'addr', '127.0.0.1')
        cfg_bbs.set('telnet', 'port', '6023')

        cfg_bbs.add_section('ssh')
        try:
            # pylint: disable=W0612
            #         Unused variable 'x84'
            import ssh  # noqa
            cfg_bbs.set('ssh', 'enabled', 'yes')

        except ImportError:
            cfg_bbs.set('ssh', 'enabled', 'no')

        cfg_bbs.set('ssh', 'addr', '127.0.0.1')
        cfg_bbs.set('ssh', 'port', '6022')
        cfg_bbs.set('ssh', 'hostkey', os.path.expanduser(
            os.path.join('~', '.x84', 'ssh_host_rsa_key')))
        cfg_bbs.set('ssh', 'hostkeybits', '2048')

        cfg_bbs.add_section('sftp')
        cfg_bbs.set('sftp', 'enabled', 'no')
        cfg_bbs.set('sftp', 'root', os.path.expanduser(
            os.path.join('~', 'x84-sftp_root')))

        try:
            os.makedirs(
                os.path.join(cfg_bbs.get('sftp', 'root'), "__uploads__"))

        except OSError:
            pass

        cfg_bbs.set('sftp', 'uploads_filemode', '644')

        # rlogin only works on port 513
        cfg_bbs.add_section('rlogin')
        cfg_bbs.set('rlogin', 'enabled', 'no')
        cfg_bbs.set('rlogin', 'addr', '127.0.0.1')
        cfg_bbs.set('rlogin', 'port', '513')

        # web
        cfg_bbs.add_section('web')
        cfg_bbs.set('web', 'enabled', 'no')
        cfg_bbs.set('web', 'port', '443')
        cfg_bbs.set('web', 'cert', os.path.expanduser(os.path.join('~', '.x84', 'ssl.cer')))
        cfg_bbs.set('web', 'key', os.path.expanduser(os.path.join('~', '.x84', 'ssl.key')))
        cfg_bbs.set('web', 'chain', os.path.expanduser(os.path.join('~', '.x84', 'ca.cer')))
        cfg_bbs.set('web', 'modules', 'static, msgserve, favicon')

        # default path if cmd argument is not absolute,
        cfg_bbs.add_section('door')
        cfg_bbs.set('door', 'path', '/usr/local/bin:/usr/games')

        cfg_bbs.add_section('matrix')
        cfg_bbs.set('matrix', 'newcmds', 'new, apply')
        cfg_bbs.set('matrix', 'byecmds', 'exit, logoff, bye, quit')
        cfg_bbs.set('matrix', 'anoncmds', 'anonymous')
        cfg_bbs.set('matrix', 'script', 'matrix')
        cfg_bbs.set('matrix', 'script_telnet', 'matrix')
        cfg_bbs.set('matrix', 'script_ssh', 'matrix_ssh')
        cfg_bbs.set('matrix', 'script_sftp', 'matrix_sftp')
        cfg_bbs.set('matrix', 'topscript', 'top')
        cfg_bbs.set('matrix', 'enable_anonymous', 'no')
        cfg_bbs.set('matrix', 'enable_pwreset', 'yes')

        cfg_bbs.add_section('session')
        cfg_bbs.set('session', 'tap_input', 'no')
        cfg_bbs.set('session', 'tap_output', 'no')
        cfg_bbs.set('session', 'tap_events', 'no')
        cfg_bbs.set('session', 'tap_db', 'no')
        cfg_bbs.set('session', 'default_encoding', 'utf8')

        cfg_bbs.add_section('irc')
        cfg_bbs.set('irc', 'server', 'efnet.portlane.se')
        cfg_bbs.set('irc', 'port', '6667')
        cfg_bbs.set('irc', 'channel', '#1984')
        cfg_bbs.set('irc', 'enable_privnotice', 'yes')
        cfg_bbs.set('irc', 'maxnick', '9')
        cfg_bbs.set('irc', 'ssl', 'no')

        cfg_bbs.add_section('shroo-ms')
        cfg_bbs.set('shroo-ms', 'enabled', 'no')
        cfg_bbs.set('shroo-ms', 'idkey', '')
        cfg_bbs.set('shroo-ms', 'restkey', '')

        # new user account script
        cfg_bbs.add_section('nua')
        cfg_bbs.set('nua', 'script', 'nua')
        cfg_bbs.set('nua', 'min_user', '3')
        cfg_bbs.set('nua', 'min_pass', '4')
        cfg_bbs.set('nua', 'max_user', '11')
        cfg_bbs.set('nua', 'max_pass', '16')
        cfg_bbs.set('nua', 'max_email', '30')
        cfg_bbs.set('nua', 'max_location', '24')
        cfg_bbs.set('nua', 'allow_apply', 'yes')
        invalid_handles = ', '.join((
            cfg_bbs.get('matrix', 'byecmds'),
            cfg_bbs.get('matrix', 'newcmds'),
            'anonymous', 'sysop',))
        cfg_bbs.set('nua', 'invalid_handles', invalid_handles)
        cfg_bbs.set('nua', 'handle_validation', '^[A-Za-z0-9]{3,11}$')

        cfg_bbs.add_section('msg')
        cfg_bbs.set('msg', 'max_subject', '40')
        # by default, anybody can make up a new tag. otherwise, only
        # those of the groups specified may.
        cfg_bbs.set('msg', 'moderated_tags', 'no')
        cfg_bbs.set('msg', 'tag_moderators', 'sysop, moderator')

        return cfg_bbs

    def __init_log_ini(self):
        """Return ConfigParser instance of logger defaults.

        Returns:
            configparser.RawConfigParser: Instance of the default settings.
        """
    
        cfg_log = configparser.RawConfigParser()
        cfg_log.add_section('formatters')
        cfg_log.set('formatters', 'keys', 'default')

        cfg_log.add_section('formatter_default')
        # for multiprocessing/threads, use: %(processName)s %(threadName) !
        cfg_log.set('formatter_default', 'format',
                    '%(asctime)s %(levelname)-6s '
                    '%(filename)10s:%(lineno)-3s %(message)s')
        cfg_log.set('formatter_default', 'class', 'logging.Formatter')
        cfg_log.set('formatter_default', 'datefmt', '%a-%m-%d %I:%M%p')

        cfg_log.add_section('handlers')
        cfg_log.set('handlers', 'keys', 'console, rotate_daily')

        cfg_log.add_section('handler_console')
        cfg_log.set('handler_console', 'class', 'logging.StreamHandler')
        cfg_log.set('handler_console', 'formatter', 'default')
        cfg_log.set('handler_console', 'args', 'tuple()')

        cfg_log.add_section('handler_rotate_daily')
        cfg_log.set('handler_rotate_daily', 'class',
                    'logging.handlers.TimedRotatingFileHandler')
        cfg_log.set('handler_rotate_daily', 'level', 'INFO')
        cfg_log.set('handler_rotate_daily', 'suffix', '%Y%m%d')
        cfg_log.set('handler_rotate_daily', 'encoding', 'utf8')
        cfg_log.set('handler_rotate_daily', 'formatter', 'default')
        daily_log = os.path.join(os.path.expanduser(
            os.path.join('~', '.x84', 'daily.log')))

        # If platform is Windows double the slashes to escape it.
        if os.name.startswith("nt"):
            cfg_log.set('handler_rotate_daily', 'args',
                        '"' + daily_log.replace('\\', '\\\\') + '", "midnight", 1, 60')
        # Else no.
        else:
            cfg_log.set('handler_rotate_daily', 'args',
                '"' + daily_log + '", "midnight", 1, 60')

        cfg_log.add_section('loggers')
        cfg_log.set('loggers', 'keys',
                    'root, sqlitedict, paramiko, xmodem, requests, irc')

        cfg_log.add_section('logger_root')
        cfg_log.set('logger_root', 'level', 'INFO')
        cfg_log.set('logger_root', 'formatter', 'default')
        cfg_log.set('logger_root', 'handlers', 'console, rotate_daily')

        # squelch sqlitedict's info, its rather long
        cfg_log.add_section('logger_sqlitedict')
        cfg_log.set('logger_sqlitedict', 'level', 'WARN')
        cfg_log.set('logger_sqlitedict', 'formatter', 'default')
        cfg_log.set('logger_sqlitedict', 'handlers', 'console, rotate_daily')
        cfg_log.set('logger_sqlitedict', 'qualname', 'sqlitedict')

        # squelch paramiko.transport info, also too verbose
        cfg_log.add_section('logger_paramiko')
        cfg_log.set('logger_paramiko', 'level', 'WARN')
        cfg_log.set('logger_paramiko', 'formatter', 'default')
        cfg_log.set('logger_paramiko', 'handlers', 'console, rotate_daily')
        cfg_log.set('logger_paramiko', 'qualname', 'paramiko.transport')

        # squelch xmodem's debug, too verbose
        cfg_log.add_section('logger_xmodem')
        cfg_log.set('logger_xmodem', 'level', 'INFO')
        cfg_log.set('logger_xmodem', 'formatter', 'default')
        cfg_log.set('logger_xmodem', 'handlers', 'console, rotate_daily')
        cfg_log.set('logger_xmodem', 'qualname', 'xmodem')

        # squelch requests to warn, too verbose
        cfg_log.add_section('logger_requests')
        cfg_log.set('logger_requests', 'level', 'WARN')
        cfg_log.set('logger_requests', 'formatter', 'default')
        cfg_log.set('logger_requests', 'handlers', 'console, rotate_daily')
        cfg_log.set('logger_requests', 'qualname', 'requests')

        # squelch irc debug, privacy-invasive
        cfg_log.add_section('logger_irc')
        cfg_log.set('logger_irc', 'level', 'INFO')
        cfg_log.set('logger_irc', 'formatter', 'default')
        cfg_log.set('logger_irc', 'handlers', 'console, rotate_daily')
        cfg_log.set('logger_irc', 'qualname', 'irc.client')

        return cfg_log

#endregion

#region Public Methods

    @staticmethod
    def instance():
        """Instance of the application settings.
        """

        return ApplicationSettings.__instance

    @staticmethod
    def cfg_bbs():
        return ApplicationSettings.instance().__cfg_bbs

    @staticmethod
    def get_ini(section=None, key=None, getter='get', split=False, splitsep=','):
        """Get an ini configuration of ``section`` and ``key``.

        If the option does not exist, an empty list, string, or False
        is returned -- return type decided by the given arguments.

        Args:
            section (_type_, optional): _description_. Defaults to None.
            key (_type_, optional): _description_. Defaults to None.
            getter (str, optional): _description_. Defaults to 'get'.
            split (bool, optional): _description_. Defaults to False.
            splitsep (str, optional): _description_. Defaults to ','.

        Returns:
            _type_: _description_
        """

        assert section is not None, section
        assert key is not None, key

        if ApplicationSettings.__instance is None:
            # when building documentation, 'get_ini' at module-level
            # imports is not really an error.  However, if yo're importing
            # a module that calls get_ini before the config system is
            # initialized, then yo're going to get an empty value! warning!!
            stack = inspect.stack()
            caller_mod, caller_func = stack[2][1], stack[2][3]
            warnings.warn('ini system not (yet) initialized, '
                        'caller = {}:{}'.format(caller_mod, caller_func))

        elif ApplicationSettings.cfg_bbs().has_option(section, key):
            getter = getattr(ApplicationSettings.cfg_bbs(), getter)
            value = getter(section, key)

            if split and hasattr(value, 'split'):
                return [_value.strip() for _value in value.split(splitsep)]

            return value

        if getter == 'getboolean':
            return False

        if split:
            return []

        return ''

#endregion
