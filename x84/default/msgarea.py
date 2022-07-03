"""
Message area for x/84.

This script provides an interface to check for new
messages, subscribe to and browse tags and networks,
find all, or unread messages, or all messages since
last login.

It determines a set of message-ids that are then
forwarded to the message browser interface.
"""
# std imports
import collections
import datetime
import fnmatch
import difflib

# local
from bbs import (
    syncterm_setfont,
    ScrollingEditor,
    list_privmsgs,
    decode_pipe,
    getterminal,
    getsession,
    LineEditor,
    list_users,
    list_msgs,
    list_tags,
    get_ini,
    get_msg,
    timeago,
    DBProxy,
    gosub,
    echo,
    Msg,
)
from common import (
    render_menu_entries,
    show_description,
    display_banner,
    display_prompt,
    prompt_pager,
    waitprompt,
)

# 3rd-party
import dateutil

TIME_FMT = '%A %b-%d, %Y at %r UTC'

#: banner art displayed in main()
art_file = get_ini(
    section='msgarea', key='art_file'
) or 'art/hx-msg.ans'

#: character encoding of banner art
art_encoding = get_ini(
    section='msgarea', key='art_encoding'
) or 'cp437'

#: preferred fontset for SyncTerm emulator
syncterm_font = get_ini(
    section='msgarea', key='syncterm_font'
) or 'topaz'

#: When set False, menu items are not colorized and render much
#: faster on slower systems (such as raspberry pi).
colored_menu_items = get_ini(
    section='msgarea', key='colored_menu_items', getter='getboolean'
) or True

#: color used for description text
color_text = get_ini(
    section='msgarea', key='color_text'
) or 'white'

#: color used for menu key entries
color_highlight = get_ini(
    section='msgarea', key='color_highlight'
) or 'bold_magenta'

#: color used for prompt
color_backlight = get_ini(
    section='msgarea', key='color_prompt',
) or 'magenta_reverse'

#: color used for brackets ``[`` and ``]``
color_lowlight = get_ini(
    section='msgarea', key='color_lowlight'
) or 'bold_black'

#: maximum length of user handles
username_max_length = get_ini(
    section='nua', key='max_user', getter='getint'
) or 10

subject_max_length = get_ini(
    section='msg', key='max_subject', getter='getint'
) or 40


def get_menu(messages):
    """ Return list of menu items by given dict ``messages``. """
    MenuItem = collections.namedtuple('MenuItem', ['inp_key', 'text'])
    items = []
    if messages['new']:
        items.extend([
            MenuItem('n', 'new ({0})'.format(len(messages['new']))),
            MenuItem('m', 'mark all read'),
        ])
    if messages['all']:
        items.append(
            MenuItem('a', 'all ({0})'.format(len(messages['all'])))
        )
    if messages['private']:
        items.append(
            MenuItem('v', 'private ({0})'.format(len(messages['private'])))
        )
    items.extend([
        MenuItem('p', 'post public'),
        MenuItem('w', 'write private'),
        MenuItem('c', 'change area'),
        MenuItem('?', 'help'),
        MenuItem('q', 'quit'),
    ])
    return items


def do_mark_as_read(session, message_indicies):
    """ Mark all given messages read. """
    session.user['readmsgs'] = (
        session.user.get('readmsgs', set()) | set(message_indicies)
    )


def get_messages_by_subscription(session, subscription):
    all_tags = list_tags()
    messages = {'all': set(), 'new': set()}
    messages_bytag = {}
    messages_read = session.user.get('readmsgs', set())

    # now occlude all private messages :)
    all_private = list_privmsgs(None)

    # this looks like perl code
    for tag_pattern in subscription:
        messages_bytag[tag_pattern] = collections.defaultdict(set)
        for tag_match in fnmatch.filter(all_tags, tag_pattern):
            msg_indicies = list_msgs(tags=(tag_match,))
            messages['all'].update(msg_indicies - all_private)
            messages_bytag[tag_pattern]['all'].update(msg_indicies - all_private)
        messages_bytag[tag_pattern]['new'] = (
            messages_bytag[tag_pattern]['all'] - messages_read)

    # and make a list of only our own
    messages['private'] = list_privmsgs(session.user.handle)

    # and calculate 'new' messages
    messages['new'] = (messages['all'] | messages['private']) - messages_read

    return messages, messages_bytag


def describe_message_area(term, subscription, messages_bytags, colors):
    get_num = lambda lookup, tag_pattern, grp: len(lookup[tag_pattern][grp])
    return ''.join((
        colors['highlight']('msgarea: '),
        colors['text'](', ').join((
            ''.join((
                quote(tag_pattern, colors),
                '({num_new}/{num_all})'.format(
                    num_new=get_num(messages_bytags, tag_pattern, 'new'),
                    num_all=get_num(messages_bytags, tag_pattern, 'all'))
            )) for tag_pattern in subscription)),
        '\r\n\r\n',
    ))


def validate_tag_patterns(tag_patterns):
    all_tags = list_tags() or set(['public'])
    removed = []
    for tag_pattern in set(tag_patterns):
        if not fnmatch.filter(all_tags, tag_pattern):
            removed.append(tag_pattern)
            tag_patterns.remove(tag_pattern)
    return removed, tag_patterns


def quote(txt, colors):
    return ''.join((('"'), colors['highlight'](txt), ('"')))


def do_describe_available_tags(term, colors):
    sorted_tags = sorted([(len(list_msgs(tags=(tag,))), tag)
                          for tag in list_tags() or ['public']
                          ], reverse=True)
    decorated_tags = [
        colors['text'](tag) +
        colors['lowlight']('({0})'.format(num_msgs))
        for num_msgs, tag in sorted_tags]

    description = ''.join((
        colors['highlight']('available tags'), ': ',
        colors['text'](', ').join(decorated_tags),
        colors['text']('.'),
    ))
    return show_description(term, description, color=None)


def get_network_tag_description(term, colors):
    """ Return description text of message networks, if any. """
    server_tags = get_ini('msg', 'server_tags', split=True)
    network_tags = get_ini('msg', 'network_tags', split=True)

    if not (network_tags or server_tags):
        return ''
    return ''.join((
        '\r\n\r\n',
        colors['text']('This board participates in intra-bbs '
                       'messaging, '),
        ''.join((
            colors['text']('hosting network messages by tag '),
            ', '.join(quote(tag, colors) for tag in server_tags),
        )) if server_tags else '',
        (colors['text'](
            ' and ') if (server_tags and network_tags) else ''),
        ''.join((
            colors['text']('participating in network messages by tag '),
            ', '.join(quote(tag, colors) for tag in network_tags),
        )) if network_tags else '',
        '.',
    ))


def do_describe_message_system(term, colors):
    """ Display help text about message tagging. """

    def describe_group_tags():
        groups = getsession().user.groups
        if not groups:
            return ''

        return ''.join((
            '\r\n\r\n',
            colors['text'](
                'Finally, private messages may be shared among groups.  You '
                'may post messages to any group you are a member of: '),
            colors['text'](
                ', '.join(quote(grp, colors) for grp in groups)),
            colors['text']('.')
        ))

    description = ''.join((
        '\r\n',
        colors['text'](
            'You can think of tags as a system of providing context to any '
            'message stored on this system.  A tag might provide the '
            'general label of the topic of conversation, which may be '
            'subscribed to.  For example, '),
        quote('python', colors),
        colors['text'](
            ' may be used for topics related to the python programming '
            'language.  This is similar to flicker or gmail tags, or '
            'hashtags.  Public messages are always tagged '),
        quote('public', colors),
        colors['text']('.  '),
        get_network_tag_description(term, colors),
        '\r\n\r\n',
        colors['text'](
            'Furthermore, glob expressions may be used such as '),
        quote('*', colors),
        ' ',
        colors['text']('for all messages, or expression '),
        quote('lang-*', colors),
        ' ',
        colors['text']('might subscribe to both '),
        quote('lang-python', colors),
        colors['text'](' and '),
        quote('lang-go', colors),
        colors['text']('.'),
        describe_group_tags(),
    ))
    return show_description(term, description, color=None)


def prompt_subscription(session, term, yloc, subscription, colors):
    """
    This function is called to assign a new set of subscription
    tags for a user.  If escape is pressed, the existing value
    is used, or '*' is used if not previously set.

    This should be called for first-time users, and optionally
    at any later time to change a subscription.
    """

    if session.user.get('msg_subscription', None) is None:
        # force-display introductory description for first-time users.
        yloc += do_describe_message_system(term, colors)
        echo('\r\n\r\n')
        yloc += 2

    # remind ourselves of all available tags
    yloc += do_describe_available_tags(term, colors) + 2

    # for small screens, scroll and leave room for prompt & errors
    if yloc > term.height + 3:
        echo('\r\n' * 3)
        yloc = term.height - 3

    # and prompt for setting of message tags
    xloc = max(0, (term.width // 2) - 40)
    input_prefix = ':: subscription tags:'
    echo(''.join((term.move(yloc, xloc), input_prefix)))

    xloc += len(input_prefix)
    wide = min(40, (term.width - xloc - 2))

    while True:
        editor = ScrollingEditor(xloc=xloc, yloc=yloc - 1, width=wide,
                                 colors={'highlight': colors['backlight']},
                                 content=', '.join(subscription),
                                 max_length=100)

        # Prompt for and evaluate the given input, splitting by comma,
        # removing any empty items, and defaulting to ['*'] on escape.
        inp = editor.read() or ''
        subscription = filter(None, set(map(unicode.strip, inp.split(',')))
                              ) or set(['*'])

        # Then, reduce to only validate tag patterns, tracking those
        # that do not match any known tags, and display a warning and
        # re-prompt if any are removed.
        removed, subscription = validate_tag_patterns(subscription)

        # clear existing warning, if any
        echo(''.join((term.normal, '\r\n\r\n', term.clear_eos)))
        if removed:
            # and display any unmatched tags as a warning, re-prompt
            txt = ''.join((
                term.bold_red(u"The following patterns are not matched: "),
                ', '.join(removed)))
            show_description(term, txt, color=None)
            continue

        # otherwise everything is fine,
        # return new subscription set
        return subscription


def allow_tag(session, idx):
    """
    Whether user is allowed to tag a message.

    :rtype: bool

    A user can tag a message if the given session's user is:

    * the message author or recipient.
    * a member of sysop or moderator group.
    * a member of any existing tag-matching user group.
    """
    moderated = get_ini('msg', 'moderated_tags', getter='getboolean')
    tag_moderators = set(get_ini('msg', 'tag_moderators', split=True))
    if not moderated and 'sysop' in session.user.groups:
        return True

    elif moderated and (tag_moderators | session.user.groups):
        # tags are moderated, but user is one of the moderator groups
        return True

    msg = get_msg(idx)
    if session.user.handle in (msg.recipient, msg.author):
        return True

    for tag in msg.tags:
        if tag in session.user.groups:
            return True
    return False


def create_reply_message(session, idx):
    """ Given a message ``idx``, create and return a replying message. """
    parent_msg = get_msg(idx)
    msg = Msg()
    msg.parent = parent_msg.idx

    # flip from/to
    msg.recipient = parent_msg.author
    msg.author = session.user.handle

    # quote message body
    msg.body = quote_body(parent_msg)

    # duplicate subject and tags
    msg.subject = parent_msg.subject
    msg.tags = parent_msg.tags

    return msg


def quote_body(msg):
    """ Return quoted body of given message, ``msg``. """
    # chose a header separator, we iterate through each one, finding any that
    # may already be used, we use whichever is used least, or the one following
    # the last used.  The given quotesep_chars is modeled after
    # reStructuredText.
    quotesep_len = 60
    quotesep_chars = u"=-`'~*+^"
    # assign quotesep_char as quotesep_chars index ([1]) of
    # lowest-order/fewest uses of quote character([0]).
    quotesep_char = quotesep_chars[sorted(
        [(msg.body.count(given_sep * quotesep_len),
          quotesep_chars.index(given_sep))
         for given_sep in quotesep_chars])[0][1]]
    txt_sent = msg.stime.replace(
        tzinfo=dateutil.tz.tzlocal()
    ).astimezone(dateutil.tz.tzutc()).strftime(TIME_FMT)
    txt_who = '|13{0}|07'.format(msg.author)
    return ('On {txt_sent}, {txt_who} wrote:\r\n'
            '{quotesep}\r\n{msg.body}\r\n{quotesep}'
            .format(txt_sent=txt_sent, txt_who=txt_who,
                    quotesep=(quotesep_char * quotesep_len),
                    msg=msg))


def display_message(session, term, msg_index, colors):
    """ Format message of index ``idx``. """
    color_handle = lambda handle: (
        colors['highlight'](handle)
        if handle == session.user.handle
        else handle)
    msg = get_msg(msg_index)
    txt_sent = msg.stime.replace(
        tzinfo=dateutil.tz.tzlocal()
    ).astimezone(dateutil.tz.tzutc()).strftime(TIME_FMT)
    txt_sentago = colors['highlight'](
        timeago((datetime.datetime.now() - msg.stime)
                .total_seconds()).strip())
    txt_to = color_handle(msg.recipient)
    txt_private = (colors['highlight'](' (private)')
                   if not 'public' in msg.tags else '')
    txt_from = color_handle(msg.author)
    txt_tags = ', '.join((quote(tag, colors)
                           for tag in msg.tags))
    txt_subject = colors['highlight'](msg.subject)
    txt_body = decode_pipe(msg.body)
    txt_breaker = ('-' if session.encoding == 'ansi' else '\u2500'
                   ) * min(80, term.width)
    msg_txt = (
        '\r\n{txt_breaker}\r\n'
        '   from: {txt_from}\r\n'
        '     to: {txt_to}{txt_private}\r\n'
        '   sent: {txt_sent} ({txt_sentago} ago)\r\n'
        '   tags: {txt_tags}\r\n'
        'subject: {txt_subject}\r\n'
        '\r\n'
        '{txt_body}\r\n'
        .format(txt_breaker=txt_breaker,
                txt_from=txt_from, txt_to=txt_to,
                txt_sent=txt_sent, txt_sentago=txt_sentago,
                txt_tags=txt_tags, txt_subject=txt_subject,
                txt_body=txt_body, txt_private=txt_private))

    do_mark_as_read(session, [msg_index])

    prompt_pager(content=msg_txt.splitlines(), line_no=0,
                 width=min(80, term.width),
                 colors=colors, breaker='- ', end_prompt=False,
                 break_long_words=True)


def can_delete(session):
    moderated = get_ini('msg', 'moderated_tags', getter='getboolean')
    tag_moderators = set(get_ini('msg', 'tag_moderators', split=True))
    return ('sysop' in session.user.groups or
            moderated and tag_moderators & session.user.groups)


def delete_message(msg):
    """ Experimental message delete! """
    # ! belongs as msg.delete() function !
    msg.recipient = ''
    msg.subject = ''
    msg.body = ''
    msg.children = set()
    msg.parent = None
    msg.tags = set()
    msg.save()
    with DBProxy('tags') as tag_db:
        for key, values in tag_db.items()[:]:
            if msg.idx in values:
                newvalue = values - set([msg.idx])
                if newvalue:
                    tag_db[key] = newvalue
                else:
                    # no more messages by this tag, delete it
                    del tag_db[key]
    with DBProxy('privmsg') as priv_db:
        for key, values in priv_db.items()[:]:
            if msg.idx in values:
                priv_db[key] = values - set([msg.idx])
    with DBProxy('msgbase') as msg_db:
        del msg_db['%d' % int(msg.idx)]


def do_reader_prompt(session, term, index, message_indices, colors):
    xpos = max(0, (term.width // 2) - (80 // 2))
    opts = []
    if index:
        opts += (('p', 'rev'),)
    if index < len(message_indices) - 1:
        opts += (('n', 'ext'),)
    if allow_tag(session, message_indices[index]):
        opts += (('e', 'dit tags'),)
    if can_delete(session):
        opts += (('D', 'elete'),)
    opts += (('r', 'eply'),)
    opts += (('q', 'uit'),)
    opts += (('idx', ''),)
    while True:
        echo(term.move_x(xpos))
        echo(''.join((
            colors['lowlight']('['),
            colors['highlight'](str(index + 1)),
            '/{0}'.format(len(message_indices)),
            colors['lowlight'](']'),
            ' ',
            ', '.join((
                ''.join((colors['lowlight']('['),
                          colors['highlight'](key),
                          colors['lowlight'](']'),
                          value
                          )) for key, value in opts)),
            ': ',
            term.clear_eol,
        )))
        width = max(2, len(str(len(message_indices))))
        inp = LineEditor(width, colors={'highlight': colors['backlight']}).read()
        if inp is None or inp.lower() == 'q':
            return None
        elif inp in ('n', ''):
            # 'n'ext or return key
            echo(term.move_x(xpos) + term.clear_eol)
            if index == len(message_indices) - 1:
                # no more messages,
                return None
            return index + 1
        elif inp == 'p' and index > 0:
            # prev
            echo(term.move_x(xpos) + term.clear_eol)
            return index - 1
        elif inp == 'e' and allow_tag(session, message_indices[index]):
            msg = get_msg(message_indices[index])
            echo('\r\n')
            if prompt_tags(session=session, term=term, msg=msg,
                           colors=colors, public='public' in msg.tags):
                echo('\r\n')
                msg.save()
            return index
        elif inp == 'D' and can_delete(session):
            delete_message(msg=get_msg(message_indices[index]))
            return None
        elif inp == 'r':
            # write message reply
            msg = create_reply_message(session=session,
                                       idx=message_indices[index])
            if (
                    prompt_subject(
                        term=term, msg=msg, colors=colors
                    ) and prompt_body(
                        term=term, msg=msg, colors=colors
                    ) and prompt_tags(
                        session=session, term=term, msg=msg,
                        colors=colors, public='public' in msg.tags
                    )):
                do_send_message(session=session, term=term,
                                msg=msg, colors=colors)
            break
        else:
            # not a valid input option, is it a valid integer? (even '-1'!)
            try:
                val = int(inp)
            except ValueError:
                # some garbage; try again
                term.inkey(0.15)
                continue
            try:
                # allow a message index, (even pythonic '-1' for 'last')
                if val > 0:
                    # 1-based indexing
                    val -= 1
                nxt_idx = message_indices.index(message_indices[val])
                if nxt_idx != index:
                    echo(term.move_x(xpos) + term.clear_eol)
                    return nxt_idx
            except (IndexError, ValueError):
                # invalid index; try again
                term.inkey(0.15)
                continue


def read_messages(session, term, message_indices, colors):
    """ Read list of given messages. """
    index = 0
    while True:
        session.activity = ('reading msgs [{0}/{1}]'
                            .format(index + 1, len(message_indices)))
        display_message(session=session, term=term,
                        msg_index=message_indices[index],
                        colors=colors)
        index = do_reader_prompt(session=session, term=term, index=index,
                                 message_indices=message_indices,
                                 colors=colors)
        if index is None:
            break


def main(quick=False):
    """ Main procedure. """

    session, term = getsession(), getterminal()
    session.activity = 'checking for new messages'

    # set syncterm font, if any
    if term.kind.startswith('ansi'):
        echo(syncterm_setfont(syncterm_font))

    colors = dict(
        highlight=lambda txt: txt,
        lowlight=lambda txt: txt,
        backlight=lambda txt: txt,
        text=lambda txt: txt
    ) if not colored_menu_items else dict(
        highlight=getattr(term, color_highlight),
        lowlight=getattr(term, color_lowlight),
        backlight=getattr(term, color_backlight),
        text=getattr(term, color_text))

    yloc = top_margin = 0
    subscription = session.user.get('msg_subscription', [])
    dirty = 2

    while True:
        if dirty == 2:
            # display header art,
            yloc = display_banner(art_file, encoding=art_encoding, center=True)
            xloc = max(0, (term.width // 2) - 40)
            echo('\r\n')
            top_margin = yloc = (yloc + 1)

        elif dirty:
            echo(term.move(top_margin, 0) + term.normal + term.clear_eos)
            echo(term.move(top_margin, xloc))

        if dirty:

            if not subscription:
                # prompt the user for a tag subscription, and loop
                # back again when completed to re-draw and show new messages.
                subscription = session.user['msg_subscription'] = (
                    prompt_subscription(
                        session=session, term=term, yloc=top_margin,
                        subscription=subscription, colors=colors))
                continue

            messages, messages_bytags = get_messages_by_subscription(
                session, subscription)

            # When quick login ('y') selected in top.py, return immediately
            # when no new messages are matched any longer.
            if quick and not messages['new']:
                echo(term.move_x(xloc) + '\r\nNo new messages.\r\n')
                return waitprompt(term)

            txt = describe_message_area(
                term=term, subscription=subscription,
                messages_bytags=messages_bytags, colors=colors)

            yloc = top_margin + show_description(
                term=term, description=txt, color=None,
                subsequent_indent=' ' * len('message area: '))

            echo(render_menu_entries(
                term=term, top_margin=yloc,
                menu_items=get_menu(messages),
                colors=colors, max_cols=2))
            echo(display_prompt(term=term, colors=colors))
            echo(colors['backlight'](' \b'))
            dirty = False

        event, data = session.read_events(('refresh', 'newmsg', 'input'))

        if event == 'refresh':
            # screen resized, redraw.
            dirty = 2
            continue

        elif event == 'newmsg':
            # When a new message is sent, 'newmsg' event is broadcasted.
            session.flush_event('newmsg')
            nxt_msgs, nxt_bytags = get_messages_by_subscription(
                session, subscription)
            if nxt_msgs['new'] - messages['new']:
                # beep and re-display when a new message has arrived.
                echo('\b')
                messages, messages_bytags = nxt_msgs, nxt_bytags
                dirty = True
                continue

        elif event == 'input':
            # on input, block until carriage return
            session.buffer_input(data, pushback=True)
            given_inp = LineEditor(
                1, colors={'highlight': colors['backlight']}
            ).read()

            if given_inp is None:
                # escape/cancel
                continue

            inp = given_inp.strip()
            if inp.lower() in ('n', 'a', 'v'):
                # read new/all/private messages
                message_indices = sorted(list(
                    {'n': messages['new'],
                     'a': messages['all'],
                     'v': messages['private'],
                     }[inp.lower()]))
                if message_indices:
                    dirty = 2
                    read_messages(session=session, term=term,
                                  message_indices=message_indices,
                                  colors=colors)
            elif inp.lower() == 'm' and messages['new']:
                # mark all messages as read
                dirty = 1
                do_mark_as_read(session, messages['new'])
            elif inp.lower() in ('p', 'w'):
                # write new public/private message
                dirty = 2
                public = bool(inp.lower() == 'p')
                msg = Msg()
                if (
                        not prompt_recipient(
                            term=term, msg=msg,
                            colors=colors, public=public
                        ) or not prompt_subject(
                            term=term, msg=msg, colors=colors
                        ) or not prompt_body(
                            term=term, msg=msg, colors=colors
                        ) or not prompt_tags(
                            session=session, term=term, msg=msg,
                            colors=colors, public=public
                        )):
                    continue
                do_send_message(session=session, term=term,
                                msg=msg, colors=colors)
            elif inp.lower() == 'c':
                # prompt for new tag subscription (at next loop)
                subscription = []
                dirty = 1
            elif inp.lower() == '?':
                # help
                echo(term.move(top_margin, 0) + term.clear_eos)
                do_describe_message_system(term, colors)
                waitprompt(term)
                dirty = 2
            elif inp.lower() == 'q':
                return
            if given_inp:
                # clear out line editor prompt
                echo(colors['backlight']('\b \b'))


def prompt_recipient(term, msg, colors, public=True):
    """ Prompt for recipient of message. """
    xpos = max(0, (term.width // 2) - (80 // 2))
    echo(term.move_x(xpos) + term.clear_eos)
    echo('Enter handle{0}.\r\n'.format(
        ', empty to address to all' if public else ''))
    echo(term.move_x(xpos) + ':: ')
    inp = LineEditor(username_max_length, msg.recipient,
                     colors={'highlight': colors['backlight']}
                     ).read()

    if inp is None:
        echo(''.join((term.move_x(xpos),
                       colors['highlight']('Canceled.'),
                       term.clear_eol)))
        term.inkey(1)
        return False

    elif not inp.strip():
        # empty, recipient is None
        msg.recipient = None
        if public:
            return True
        return False

    inp = inp.strip()

    # validate/find user
    userlist = list_users()
    if inp in userlist:
        # exact match,
        msg.recipient = inp
        echo('\r\n')
        return True

    # nearest match
    for match in difflib.get_close_matches(inp.strip(), userlist):
        echo(''.join((
            term.move_x(xpos),
            '{0} [yn]'.format(colors['highlight'](match)),
            term.clear_eol,
            ' ?\b\b')))
        while True:
            inp = term.inkey()
            if inp.code == term.KEY_ESCAPE:
                # escape/cancel
                return False
            elif inp.lower() == 'y':
                # accept match
                msg.recipient = match
                echo('\r\n')
                return True
            elif inp.lower() == 'n':
                # next match
                break

    echo(''.join((term.move_x(xpos),
                   colors['highlight']('No match.'),
                   term.clear_eol)))
    term.inkey(1)
    return False


def prompt_subject(term, msg, colors):
    """ Prompt for subject of message. """
    xpos = max(0, (term.width // 2) - (80 // 2))
    echo(''.join((term.move_x(xpos),
                   term.clear_eos,
                   'Enter Subject.\r\n',
                   term.move_x(xpos),
                   ':: ')))
    inp = LineEditor(subject_max_length, msg.subject,
                     colors={'highlight': colors['backlight']}
                     ).read()

    if inp is None or not inp.strip():
        echo(''.join((term.move_x(xpos),
                       colors['highlight']('Canceled.'),
                       term.clear_eol)))
        term.inkey(1)
        return False

    msg.subject = inp.strip()
    return True


def prompt_body(term, msg, colors):
    """ Prompt for and set 'body' of message by executing 'editor' script. """
    with term.fullscreen():
        content = gosub('editor', save_key=None,
                        continue_draft=msg.body)
    # set syncterm font, if any
    if term.kind.startswith('ansi'):
        echo(syncterm_setfont(syncterm_font))
    echo(term.move(term.height, 0) + term.normal + '\r\n')
    if content and content.strip():
        msg.body = content
        return True
    xpos = max(0, (term.width // 2) - (80 // 2))
    echo(''.join((term.move_x(xpos),
                   colors['highlight']('Message canceled.'),
                   term.clear_eol)))
    term.inkey(1)
    return False


def prompt_tags(session, term, msg, colors, public=True):
    xpos = max(0, (term.width // 2) - (80 // 2))

    # conditionally enforce tag moderation
    moderated = get_ini('msg', 'moderated_tags', getter='getboolean')
    tag_moderators = set(get_ini('msg', 'tag_moderators', split=True))

    # enforce 'public' tag
    if public and 'public' not in msg.tags:
        msg.tags.add('public')
    elif not public and 'public' in msg.tags:
        msg.tags.remove('public')

    # describe all available tags, as we oft want to do.
    do_describe_available_tags(term, colors)

    # and remind ourselves of the available network tags,
    description = get_network_tag_description(term, colors)
    if description:
        show_description(term=term, color=None, description=description)

    echo(''.join((term.move_x(xpos),
                   term.clear_eos,
                   'Enter tags, separated by commas.\r\n',
                   term.move_x(xpos),
                   ':: ')))

    all_tags = list_tags()

    while True:
        inp = LineEditor(subject_max_length, ', '.join(sorted(msg.tags)),
                         colors={'highlight': colors['backlight']}
                         ).read()
        if inp is None:
            echo(''.join((term.move_x(xpos),
                           colors['highlight']('Message canceled.'),
                           term.clear_eol)))
            term.inkey(1)
            return False

        msg.tags = set(filter(None, set(map(unicode.strip, inp.split(',')))))
        if moderated and not (tag_moderators | session.user.groups):
            cannot_tag = [_tag for _tag in msg.tags if _tag not in all_tags]
            if cannot_tag:
                echo(''.join(('\r\n', term.move_x(xpos),
                               ', '.join((quote(tag, colors)
                                           for tag in cannot_tag)),
                               ': not allowed; this system is moderated.')))
                term.inkey(2)
                echo(term.move_up)
                map(msg.tags.remove, cannot_tag)
                continue

        return True


def do_send_message(session, term, msg, colors):
    xpos = max(0, (term.width // 2) - (80 // 2))
    msg.save()
    do_mark_as_read(session, [msg.idx])
    echo(''.join(('\r\n',
                   term.move_x(xpos),
                   colors['highlight']('message sent!'))))
    session.send_event('global', ('newmsg', msg.idx,))
    term.inkey(1)
