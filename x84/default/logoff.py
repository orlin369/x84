""" logoff script with 'automsg' for x/84. """


def main():
    """ Main procedure. """
    # pylint: disable=R0914,R0912
    #         Too many local variables
    #         Too many branches
    from bbs import DBProxy, getsession, getterminal, echo
    from bbs import ini, LineEditor, timeago, showart
    from bbs import disconnect
    import time
    import os
    session, term = getsession(), getterminal()
    session.activity = 'logging off'
    handle = session.user.handle or 'anonymous'
    max_user = ini.CFG.getint('nua', 'max_user')
    prompt_msg = '[spnG]: ' if session.user.get('expert', False) else (
        '%s:AY SOMEthiNG %s:REViOUS %s:EXt %s:Et thE fUCk Off !\b' % (
            term.bold_blue_underline('s'),
            term.bold_blue_underline('p'),
            term.bold_blue_underline('n'),
            term.red_underline('Escape/g'),))
    prompt_say = ''.join((term.bold_blue(handle),
                           term.bold_blue(' SAYS WhAt'), term.bold(': '),))
    boards = (('htc.zapto.org', 'Haunting the Chapel', 'Mercyful fate',),
              ('bbs.force9.org', 'fORCE9 (Euro HQ!)', 'RiPuk',),
              ('bbs.pharcyde.org', 'Pharcyde BBS', 'Access Denied',),
              ('blackflag.acid.org', 'The BLACK fLAG - ACiD Telnet HQ', 'Caphood',),
              ('oddnetwork.org', '79 columns', 'Haliphax'),)
    board_fmt = '%25s %-30s %-15s\r\n'
    goodbye_msg = ''.join((
        term.move(term.height, 0),
        '\r\n' * 10,
        'tRY ANOthER fiNE bOARd', term.bold(':'), '\r\n\r\n',
        board_fmt % (
            term.underline('host'.rjust(25)),
            term.underline('board'.ljust(30)),
            term.underline('sysop'.ljust(15)),),
        '\r\n'.join([board_fmt % (
            term.bold(host.rjust(25)),
            term.reverse(board.center(30)),
            term.bold_underline(sysop),)
            for (host, board, sysop) in boards]),
        '\r\n\r\n',
        term.bold(
            'back to the mundane world...'),
        '\r\n',))
    commit_msg = term.bold_blue(
        '-- !  thANk YOU fOR YOUR CONtRibUtiON, bROthER  ! --')
    write_msg = term.red_reverse(
        'bURNiNG tO ROM, PlEASE WAiT ...')
    db_firstrecord = ((time.time() - 1984,
                       'B. b.', 'bEhAVE YOURSElVES ...'),)
    automsg_len = 40

    def refresh_prompt(msg):
        """ Refresh automsg prompt using string msg. """
        echo(''.join(('\r\n\r\n', term.clear_eol, msg)))

    def refresh_automsg(idx):
        """ Refresh automsg database, display automsg of idx, return idx. """
        session.flush_event('automsg')
        autodb = DBProxy('automsg')
        automsgs = sorted(autodb.values()) if len(autodb) else db_firstrecord
        dblen = len(automsgs)
        # bounds check
        if idx < 0:
            idx = dblen - 1
        elif idx > dblen - 1:
            idx = 0
        tm_ago, handle, msg = automsgs[idx]
        asc_ago = '%s ago' % (timeago(time.time() - tm_ago))
        disp = ''.join(('\r\n\r\n',
                         term.bold(handle.rjust(max_user)),
                         term.bold_blue('/'),
                         term.bold_blue('%*d' % (len('%d' % (dblen,)), idx,)),
                         term.bold_blue(':'),
                         term.bold_green(msg.ljust(automsg_len)),
                         term.bold('\\'),
                         term.bold_blue(asc_ago),))
        echo('\r\n'.join(term.wrap(disp)))
        return idx

    def refresh_all(idx=None):
        """
        refresh screen, database, and return database index
        """
        echo(''.join(('\r\n\r\n', term.clear_eol,)))
        for line in showart(
                os.path.join(os.path.dirname(__file__), 'art', 'logoff.ans'), 'cp437'):
            echo(line)
        idx = refresh_automsg(-1 if idx is None else idx)
        refresh_prompt(prompt_msg)
        return idx

    idx = refresh_all()
    while True:

        if session.poll_event('refresh'):
            idx = refresh_all()
        elif session.poll_event('automsg'):
            refresh_automsg(-1)
            echo('\a')  # bel
            refresh_prompt(prompt_msg)

        inp = term.inkey(5)
        if inp.lower() == 'g' or inp.code == term.KEY_EXIT:
            # http://www.xfree86.org/4.5.0/ctlseqs.html
            # Restore xterm icon and window title from stack.
            echo(chr(27) + '[23;0t')
            echo(goodbye_msg)
            term.inkey(1.5)
            disconnect('logoff.')

        elif inp.lower() == 'n':
            idx = refresh_automsg(idx + 1)
            refresh_prompt(prompt_msg)
        elif inp.lower() == 'p':
            idx = refresh_automsg(idx - 1)
            refresh_prompt(prompt_msg)
        elif inp.lower() == 's':
            # new prompt: say something !
            refresh_prompt(prompt_say)
            msg = LineEditor(width=automsg_len).read()
            if msg is not None and msg.strip():
                echo(''.join(('\r\n\r\n', write_msg,)))
                autodb = DBProxy('automsg')
                autodb.acquire()
                idx = max([int(ixx) for ixx in autodb.keys()] or [-1]) + 1
                autodb[idx] = (time.time(), handle, msg.strip())
                autodb.release()
                session.send_event('global', ('automsg', True,))
                refresh_automsg(idx)
                echo(''.join(('\r\n\r\n', commit_msg,)))
                term.inkey(0.5)  # for effect, LoL
            # display prompt
            refresh_prompt(prompt_msg)
