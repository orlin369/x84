2.0.17
  - Begining of the migration to python 3.9+ run-time environment.

2.0.16
  - This is the *final* release of x/84, there will be no more updates!!
  - update all setup.py requirements to the latest, here's hoping the
    direct downstream dependencies honor SEMVER and this continues to
    work for many more years to come!
  - removed bbs.modem api and xmodem dependencies, it is not used
  - removed 'weather' from main menu, it is broken
  - removed 'sysop' from main menu, the "x84 message net" is dead
  - added 'ct', a 24-bit color example program (from blessed)
2.0.15
  - bugfix: upgraded six version to 1.9.0 to meet blessed requirements
  - enhancement: added 'raw' flag to x84.bbs.door.Door to send raw output to
    the session.write method. useful for incorporating external file transfer
    programs.
  - refactor: all example scripts now prefer getterminal().inkey() rather than
    deprecated getch(), getch() returns multiple types, None for timeout,
    keycode as integer for application keys, or string for characters.
    inkey() interface always returns a string, sometimes empty, with
    .code attribute for application keys.
  - This refactoring allows us to use the latest version of 'blessed'
    library.
2.0.14
  - enhancement: ability to connect to irc servers with password protection
    using 'password' setting in 'irc' section of default.ini
  - enhancement: pipe codes for colors/modes are now supported in ircchat.py.
  - bugfix: msgarea.py fix unread message count (only include messages the
    user can view)
2.0.13
  - bugfix: previously the 'stop/more/continuous' prompt was not pausing news
    output in the appropriate place. prompt_pager also deals with wrapped lines
    much better now.
  - bugfix: OpenSSL has changed a method signature in their library, which
    broke the versions of cffi and cryptography x84 relies on. increased the
    required versions of these libraries.
2.0.12
  - enhancement: [system] option scriptpath now supports a comma
    separated list of directories in which customizations are stored.
2.0.11
  - bugfix: weather.py fix incorrect postal code return from Accu Weather.
    Changed the default to populate search by city/state instead of
    postal since this is no longer returned from accu weather correctly.
    Also re-added missing save location field that was outside of
    while loop to funtion exit.
  - bugfix: tetris.py fix for sending terminal font sequence prior to
    ansi screen display instead of after.
2.0.10
  - bugfix: display updates when posting to oneliners, issue #235

2.0.9
  - bugfix: profile.py now accepts a target handle as an optional
    argument to its main() function, so online.py can successfully
    launch the profile editor for online users.
2.0.8
  - bugfix: Fixed a nasty Return value bug in vote.py that could
    cause a database failure.
  - bugfix: XML element tag name in weather.py AccuWeather response now
    includes namespace
  - bugfix: Refresh screen error in msgarea.py
  - workaround: always force refresh on event 'gosub' as terminal clients
    such as syncterm, netrunner, and etherterm do not support the
    "alt screen" sequence well, or at all.
  - sometimes (when TERM is 'ansi') sesame doors did not run.
2.0.7
  - bugfix: ValueError in profile.py for setting bad timeout value
  - bugfix: ASCII colly diz with extended chars was causing an error
  - bugfix: KeyError in hackernews.py
  - deprecation: the "extras" subfolder of default script has been
    moved to https://github.com/x84-extras

  (version 2.0.6 was not released to pypi)

2.0.5
  - bugfix: UnicodeDecodeError when quoting some messages
  - bugfix: '__uploads__' folder not hidden by sftp as intended
2.0.4
  - bugfix: sesame did not honor want_cols/rows when
    the given terminal size was already of its exact
    dimensions.
2.0.3
  - bugfix: import common.py as relative from main.py
2.0.1
  - bugfix: did not include default 'top' art
  - bugfix: could not press 'return' to continue in sesame
2.0.0
  - you will need to ensure to set 'enabled = yes' for the shroo-ms api,
    previously this was enabled if the section alone existed
  - you will need to change the values of `newcmds', `anoncmds',
    and 'byecmds' of section [matrix] to be comma-delimited,
    not space-delimited as before. Similarly, you must also change
    value of 'invalid_handles' in section [nua].
  - the meaning of [system] option 'termcap-ansi', when not valued 'no', now
    coerces any reported terminal types *beginning* with 'ansi' to
    the target type.
  - fail2ban is enabled by [fail2ban] option 'enabled = yes'. Previously,
    the mere existence of section [fail2ban] was sufficient.
  - *new* option, 'anoncmds' in section 'matrix', where previously only
    the 'anonymous' user was a legitimate synonym, you may now provide
    many different ones -- humorously, you could provide 'root'.
  - *new* option, 'script_ssh' in section 'matrix', points to a new
    login matrix script that takes new keyword arguments, 'anonymous',
    or 'new' as booleans True or False, or user keyword argument as
    string representing the (already authenticated) user handle.
  - keyword arguments for gosub() and goto() are now supported.
  - ssh key authentication support
  - *removed*: x84.bbs.log.ColoredConsoleHandler.
    If you see exception: ``ImportError: No module named log``
    simply change line, ``class = x84.bbs.log.ColoredConsoleHandler``
    to new line, ``class = logging.StreamHandler``
    in your ~/.x84/logging.ini or /etc/x84/logging.ini file!
  - new bulletins, userlist, from hellbeard
  - new door 'sesame.py' script, from maze
  - project 'blessed' has been merged. Some minor API changes that
    currently just emit a DeprecationWarning, will be removed in 2.0,
    especially in regards to sequence-safe textwrap() function, one
    should instead use term.wrap().
  - project 'wcwidth' has been merged. No change.
  - move_x now works for screen/etc. TERM types (fixed in blessed).
  - ssh server support: for existing servers, simply add a new section
    to your default.ini::
    [ssh]
    addr = 127.0.0.1
    port = 6022
    hostkey = /my/path/to/.x84/ssh_host_rsa_key
    hostkeybits = 2048
  - rudimentary web.py-based web server module (webserve.py) for API
    endpoints.
    This requires both pyOpenSSL and web.py packages, which are not
    installed by default by setup.py. It is configured with the [web]
    default.ini section (the "chain" setting is optional; only use it
    if you have a chained cert):
    [web]
    addr = 0.0.0.0
    port = 8443
    cert = /home/bbs/ssl.cer
    key = /home/bbs/ssl.key
    chain = /home/bbs/chain.cer
  - message network server web API endpoint (webmodules/msgserve.py).
  - message network REST client for pull/push (msgpoll.py).

1.1.0
  - resolve issue #53: using upstream 'blessed' fork.
  - fix issue #38: chat buffer lost on resize
  - fix issue #43: bordering math issues in msgreader
  - pull request #46, #47, #50, #54: misc. dropfile bugfixes (haliphax)
  - pull request #45: resolves CP437 issue with output_filter (haliphax)

1.0.9
  - tagging no longer requires 'moderator' or 'sysop' group by default,
    is now configurable with .ini options of section [msg]:
    moderated_tags: yes/no, tag_moderators: list of groups
  - yet even more fixes for bad xml bytes in bbs-scene.org's onelinerz api
  - thanks to xzip, weather now looks like a television broadcast layout.
  - a short/malicious sub-negotiation string will not cause engine crash.
  - default board recieved some new ami/x-style art from xzip!impure
  - resolve issues with utf8 input on slow links
  - NAWS responses of 0x0 ('ConnectBot') are ignored.
1.0.8
  - UI/bugfixes for last callers (default/lc.py) and default/ttyplay.py
1.0.6, 1.0.7
  - various issues with SyncTerm client resolved in bbs/editor.py and
    default/editor.py, notably: don't draw on bottom line (causes scroll),
    and use 'term.normal' before 'term.red_reverse' or other 'highlight'
    colors, which were otherwise rendered invisible by SyncTerm.
  - some timing negotiations lengthened for very-high latency links, and
    dec vt query removed, it was found useless, increasing connect-time.
1.0.5
  - please add/merge in new 'default.ini' and 'logging.ini' values.
    You can move away your old files, start x84, then compare. There are
    new sections such as [lord], [dosemu], and [door].
  - last callers database must be rebuilt for migrations, this is the default
    "debug" door for sysops, press ctrl + _ from the main menu to rebuild.
    otherwise only new callers will appear.
  - otherwise, this new release includes general display and bug fixes and
    door support for LORD/dosemu, bbs/door.py and default/lord.py.
