"""
Sysop area script for x/84.

Currently, this only serves the purpose of adding new message networks.
"""

from bbs import getsession, getterminal, echo, get_ini, DBProxy, LineEditor


MSG_NO_SERVER_TAGS = "no `server_tags' defined in ini file, section [msg]."


def view_leaf_msgnet(server_tag=None, board_id=None):
    if server_tag is None:
        server_tags = get_ini(section='msg', key='server_tags', split=True)
        if not server_tags:
            raise ValueError("no `server_tags' defined in ini file, "
                             "section [msg].")
        # RECURSION
        for _st in server_tags:
            view_leaf_msgnet(server_tag=_st, board_id=None)
        return

    if board_id is None:
        board_ids = DBProxy('{0}keys'.format(server_tag)).keys()
        for _bid in board_ids:
            # RECURSION
            view_leaf_msgnet(server_tag=server_tag, board_id=_bid)
        return

    with DBProxy('{0}keys'.format(server_tag)) as key_db:
        echo('\r\n[msgnet_{0}]'.format(server_tag))
        echo('\r\nurl_base = https://{addr}:{port}/'
             .format(addr=get_ini('web', 'addr'),
                     port=get_ini('web', 'port')))
        echo('\r\nboard_id = {0}'.format(board_id))
        echo('\r\ntoken = {0}'.format(key_db[board_id]))
        echo('\r\npoll_interval = 300')
        echo('\r\n')
        echo('\r\n[msg]')
        echo('\r\nnetwork_tags = {0}'.format(server_tag))
    echo('\r\n')
    echo('-' * 40)


def add_leaf_msgnet():
    import cryptography.fernet
    server_tags = get_ini(section='msg', key='server_tags', split=True)
    if not server_tags:
        raise ValueError(MSG_NO_SERVER_TAGS)

    if len(server_tags) == 1:
        server_tag = server_tags[0]
    else:
        while True:
            echo('chose a server tag: ')
            idx = 0
            for idx, tag in server_tags:
                echo('\r\n{0}. {1}'.format(idx, tag))
            echo('\r\n: ')
            inp = LineEditor(width=len(str(idx)).read())
            if inp is None:
                return
            try:
                server_tag = server_tags[int(inp)]
                break
            except ValueError:
                pass

    with DBProxy('{0}keys'.format(server_tag)) as key_db:
        board_id = max(map(int, key_db.keys()) or [-1]) + 1
        client_key = cryptography.fernet.Fernet.generate_key()
        key_db[board_id] = client_key
    echo('\r\n')
    echo('-' * 40)
    view_leaf_msgnet(server_tag, board_id)


def main():
    session, term = getsession(), getterminal()
    assert session.user.is_sysop

    dirty = True
    while True:
        if dirty:
            echo('\r\n\r\nmessage network functions:\r\n')
            echo('    [a]dd new leaf node.\r\n')
            echo('    [v]iew leaf nodes.\r\n')
            echo('\r\n\r\n')
            echo('[q]uit\r\n')
            dirty = False
        echo('\r\nsysop cmd: ')
        inp = term.inkey()
        if inp.lower() == 'q':
            echo(inp)
            echo('\r\n')
            return
        elif inp.lower() == 'a':
            echo(inp)
            add_leaf_msgnet()
            dirty = True
        elif inp.lower() == 'v':
            echo(inp)
            echo('\r\n')
            echo('-' * 40)
            view_leaf_msgnet()
            echo('\r\n\r\nPress any key.')
            term.inkey()
            dirty = True
