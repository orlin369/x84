""" top-level scripting module for x/84. """
# local side-effect producing imports
# (encodings such as 'cp437_art' become registered)
__import__('encodings.aliases')
__import__('encodings')

# local/exported at top-level 'from bbs import ...'
from bbs.ansiwin import AnsiWindow
from bbs.dbproxy import DBProxy
from bbs.door import Door, DOSDoor, Dropfile
from bbs.editor import LineEditor, ScrollingEditor
from exceptions.disconnected import Disconnected
from exceptions.goto import Goto
from bbs.lightbar import Lightbar
from bbs.msgbase import list_msgs, get_msg, list_tags, Msg, list_privmsgs
from bbs.output import (echo, timeago, encode_pipe, decode_pipe,
                            syncterm_setfont, showart, ropen,
                            from_cp437,  # deprecated in v2.0
                            )
from bbs.pager import Pager
from bbs.script_def import Script
from bbs.selector import Selector
from bbs.session import (getsession, getterminal,
                             goto, disconnect, gosub,
                             getch,      # deprecated in v2.1
                             )
from bbs.userbase import list_users, get_user, find_user, User, Group

# the scripting API is generally defined by this __all__ attribute, but
# the real purpose of __all__ is defining what gets placed into a caller's
# namespace when using statement `from bbs import *`
__all__ = ('list_users', 'get_user', 'find_user', 'User', 'Group', 'list_msgs', 'get_msg',
           'list_tags', 'Msg', 'LineEditor', 'ScrollingEditor', 'echo', 'timeago', 'AnsiWindow',
           'Selector', 'Disconnected', 'Goto', 'Lightbar', 'from_cp437', 'DBProxy', 'Pager', 'Door',
           'DOSDoor', 'goto', 'disconnect', 'getsession', 'getterminal', 'getch', 'gosub', 'ropen',
           'showart', 'Dropfile', 'encode_pipe', 'decode_pipe', 'syncterm_setfont', 'get_ini',
           'Script', 'list_privmsgs')
