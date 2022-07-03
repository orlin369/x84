""" Voting booth script for x/84. """

from common import waitprompt, prompt_pager
from bbs import getsession, getterminal, echo, LineEditor
from bbs import DBProxy, showart, syncterm_setfont
import os

databasename = 'votingbooth'  # change this to use an alternative database file

__author__ = 'Hellbeard'
__version__ = 1.2

# -----------------------------------------------------------------------------------

def ynprompt():
    term = getterminal()
    echo(term.magenta + ' (' + term.cyan + 'yes' + term.magenta +
         '/' + term.cyan + 'no' + term.magenta + ')' + term.white)
    while True:
        inp = term.inkey()
        if inp.lower() == 'y':
            yn = True
            echo(' yes!')
            break
        if inp.lower() == 'n' or inp.lower() == 'q':
            yn = False
            echo(' no')
            break
    return(yn)

# -----------------------------------------------------------------------------------

def query_question():
    term = getterminal()
    session = getsession()
    db = DBProxy(databasename)
    questions = []
    index = []
    uservotingdata = []
    questions = db['questions']
    index = db['index']

    # create a new database file if none exists
    if not session.user.handle in db:
        db[session.user.handle] = {}
    uservotingdata = db[session.user.handle]

    echo(term.clear() + term.blue('>>') + term.white('questions availible\r\n') +
         term.blue('-' * 21 + '\r\n\r\n'))

    text = ''
    for i in range(0, len(questions)):
        if (index[i], 0) in uservotingdata:
            text = text + term.green('*')
        text = text + ''.join(term.magenta + '(' + term.cyan + str(i) + term.magenta + ') ' +
                              term.white + questions[i] + '\r\n')
    text = text.splitlines()
    prompt_pager(content=text,
                 line_no=0,
                 colors={'highlight': term.cyan,
                         'lowlight': term.green,
                         },
                 width=term.width, breaker=None, end_prompt=False)
    echo(term.move_x(0) + term.bold_black('* = already voted\r\n\r\n'))

    while True:
        echo(term.move_x(
            0) + term.magenta('select one of the questions above or press enter to return: '))
        le = LineEditor(10)
        le.colors['highlight'] = term.cyan
        inp = le.read()
        if inp is not None and inp.isnumeric() and int(inp) < len(questions):
            return int(inp)
        else:
            # -1 in this case means that no valid option was chosen.. break
            # loop.
            return -1

# -----------------------------------------------------------------------------------


def list_results(questionnumber):
    term = getterminal()
    db = DBProxy(databasename)
    alternatives = {}
    questions = []
    results = []
    amount_of_alternatives = db['amount_of_alternatives']
    alternatives = db['alternatives']
    questions = db['questions']
    results = db['results']

    echo(term.clear())

    text = (term.white + questions[questionnumber] + '\r\n' + term.blue +
            '-' * len(questions[questionnumber]) + '\r\n\r\n')

    # only display full statistics if the screen width is above 79 columns.
    if term.width > 79:
        text = text + (term.magenta + '(alternatives)' + term.move_x(49) +
                       '(votes)' + term.move_x(57) + '(percentage)\r\n')
        totalvotes = 0.00
        for i in range(0, amount_of_alternatives[questionnumber]):
            totalvotes = totalvotes + results[(questionnumber, i)]
        for i in range(0, amount_of_alternatives[questionnumber]):
            if results[(questionnumber, i)] > 0:
                percentage = (results[(questionnumber, i)] / totalvotes) * 100
            else:
                percentage = 0
            staple = int(round(percentage / 5))
            text = text + ''.join(term.move_x(0) + term.white(alternatives[(questionnumber, i)]) + term.move_x(49) +
                                   term.cyan(str(results[(questionnumber, i)])) + '  ' + term.cyan + str(int(percentage)) +
                                   term.cyan('%') + term.move_x(57) + term.cyan('[') +
                                   term.green('#' * staple) + term.move_x(78) + term.cyan(']'))
            if i != amount_of_alternatives[questionnumber]:
                text = text + '\r\n'
    else:
        for i in range(0, amount_of_alternatives[questionnumber]):
            text = text + (term.white(str(alternatives[(questionnumber, i)])) + term.cyan(' votes: ') +
                           term.magenta(str(results[(questionnumber, i)])) + '\r\n')

    text = text.splitlines()
    prompt_pager(content=text,
                 line_no=0,
                 colors={'highlight': term.cyan,
                         'lowlight': term.green,
                         },
                 width=term.width, breaker=None, end_prompt=False)
    echo(term.move_x(0) + term.bold_black('* = already voted\r\n'))
    waitprompt(term)

# -----------------------------------------------------------------------------------

def vote(questionnumber):
    term = getterminal()
    session = getsession()
    db = DBProxy(databasename)
    questions = []
    amount_of_alternatives = []
    alternatives = {}
    results = {}
    index = []
    questions = db['questions']
    alternatives = db['alternatives']
    results = db['results']
    amount_of_alternatives = db['amount_of_alternatives']
    index = db['index']

    echo(term.clear() + term.white + questions[questionnumber] + '\r\n' +
         term.blue('-' * len(questions[questionnumber])) + '\r\n\r\n')
    text = ''
    for i in range(0, amount_of_alternatives[questionnumber]):
        text = text + (term.magenta + '(' + term.cyan + str(i) + term.magenta + ') ' +
                       term.white + alternatives[(questionnumber, i)] + '\r\n')

    text = text.splitlines()
    prompt_pager(content=text,
                 line_no=0,
                 colors={'highlight': term.cyan,
                         'lowlight': term.green,
                         },
                 width=term.width, breaker=None, end_prompt=False)
    echo(term.move_x(0) + term.magenta('(') + term.cyan(str(amount_of_alternatives[questionnumber])) +
         term.magenta(') ') + term.bold_black('Add your own answer..\r\n\r\n'))

    while True:
        echo(term.move_x(0) + term.magenta('Your choice: '))
        le = LineEditor(10)
        le.colors['highlight'] = term.cyan
        inp = le.read()
        if inp is not None and inp.isnumeric() and int(
                inp) <= amount_of_alternatives[questionnumber]:

            # create database for user if the user hasn't made any votes
            if session.user.handle not in db:
                db[session.user.handle] = {}

            uservotingdata = {}
            uservotingdata = db[session.user.handle]

            # if user wants to create an own alternative..
            if int(inp) == amount_of_alternatives[questionnumber]:
                echo(term.clear + term.red + '\r\nPress enter to abort. ' +
                     term.move(0, 0) + term.white('Your answer: '))
                le = LineEditor(48)
                new_alternative = le.read()
                if new_alternative == '' or new_alternative == None:
                    return
                results[(questionnumber, int(inp))] = 0  # init..
                # init..
                alternatives[(questionnumber, int(inp))] = new_alternative
                amount_of_alternatives[
                    questionnumber] = amount_of_alternatives[questionnumber] + 1
                db['alternatives'] = alternatives
                db['amount_of_alternatives'] = amount_of_alternatives

            # if the user has voted on this question before..
            if (index[questionnumber], 0) in uservotingdata:
                temp2 = uservotingdata[(index[questionnumber], 0)]
                results[(questionnumber, temp2)] = results[
                    (questionnumber, temp2)] - 1  # remove the old vote
                results[(questionnumber, int(inp))] = results[
                    (questionnumber, int(inp))] + 1
                uservotingdata[(index[questionnumber], 0)] = int(inp)
            else:
                uservotingdata[(index[questionnumber], 0)] = int(inp)
                results[(questionnumber, int(inp))] = results[
                    (questionnumber, int(inp))] + 1

            uservotingdata[(index[questionnumber], 0)] = int(inp)

            echo(term.green('\r\nyour vote has been noted, thanks..'))
            term.inkey(2)
            db['results'] = results
            db[session.user.handle] = uservotingdata
            list_results(questionnumber)
            return

# -----------------------------------------------------------------------------------

def add_question():
    term = getterminal()
    db = DBProxy(databasename)
    questions = []
    amount_of_alternatives = []
    index = {}
    alternatives = {}
    results = {}
    index = db['index']
    questions = db['questions']
    alternatives = db['alternatives']
    results = db['results']
    amount_of_alternatives = db['amount_of_alternatives']
    amount_of_questions = len(questions)

    echo(term.clear + term.white + '\r\nQuestion: ')
    le = LineEditor(65)
    new_question = le.read()
    if new_question == '' or new_question == None:
        return

    echo(term.bold_black('\r\n\r\nLeave a blank line when you are finished..'))
    new_amount = 0
    while True:
        echo(term.normal + term.white + '\r\nchoice ' +
             term.red + str(new_amount) + term.white + ': ')
        le = LineEditor(48)
        alternatives[(amount_of_questions, new_amount)] = le.read()
        if alternatives[(amount_of_questions, new_amount)] == '' or alternatives[(amount_of_questions, new_amount)] == None :
            break
        else:
            results[(amount_of_questions, new_amount)] = 0
            new_amount = new_amount + 1

    if new_amount > 0:
        echo(term.white('\r\n\r\nSave this voting question?'))
        answer = ynprompt()
        if answer == 1:
            questions.append(new_question)
            amount_of_alternatives.append(new_amount)

            indexcounter = db['indexcounter']
            indexcounter = indexcounter + 1
            index.append(str(indexcounter))

            db['indexcounter'] = indexcounter
            db['index'] = index
            db['questions'] = questions
            db['amount_of_alternatives'] = amount_of_alternatives
            db['results'] = results
            db['amount_of_questions'] = amount_of_questions
            db['alternatives'] = alternatives

            waitprompt(term)

# -----------------------------------------------------------------------------------

def delete_question(questionnumber):
    term = getterminal()
    db = DBProxy(databasename)
    alternatives = {}
    questions = []
    results = {}
    amount_of_alternatives = []
    questions = db['questions']
    results = db['results']
    amount_of_alternatives = db['amount_of_alternatives']
    alternatives = db['alternatives']
    index = db['index']

    echo(term.clear + term.white('Delete the ') + term.magenta('(') + term.cyan('e') + term.magenta(')') +
         term.white('ntire question or delete single ') + term.magenta('(') + term.cyan('a') + term.magenta(')') +
         term.white('lternatives?') + '\r\n\r\n' + term.magenta('command: '))

    le = LineEditor(10)
    le.colors['highlight'] = term.cyan
    inp = le.read()
    # makes the input indifferent to wheter you used lower case when typing in
    # a command or not..
    inp = (inp or '').lower()

    if inp == 'a':  # delete answer alternative..
        echo(term.clear)
        echo(term.white + questions[questionnumber] + term.move_x(max(0, term.width - 12)) +
             ' index: ' + str(index[questionnumber]) + '\r\n\r\n')
        for i in range(0, amount_of_alternatives[questionnumber]):
            echo(term.cyan(str(i) + '. ') +
                 term.white(alternatives[(questionnumber, i)]) + '\r\n')

        echo(term.magenta('\r\nSelect a number. Enter to abort: '))

        le = LineEditor(10)
        le.colors['highlight'] = term.cyan
        inp2 = le.read()

        if inp2 is not None and inp2.isnumeric() and int(
                inp2) < amount_of_alternatives[questionnumber]:
            if int(inp2) + 1 < amount_of_alternatives[questionnumber]:
                for i in range(
                        int(inp2), amount_of_alternatives[questionnumber] - 1):
                    alternatives[(questionnumber, i)] = alternatives[
                        (questionnumber, i + 1)]
                    results[(questionnumber, i)] = results[
                        (questionnumber, i + 1)]
        else:
            return
        amount_of_alternatives[questionnumber] -= 1

    elif inp == 'e':  # delete entire question..
        if questionnumber + 1 < len(questions):
            for i in range(questionnumber, len(questions) - 1):
                questions[i] = questions[i + 1]
                amount_of_alternatives[i] = amount_of_alternatives[i + 1]
                index[(i)] = index[(i + 1)]
                for i2 in range(0, amount_of_alternatives[i + 1]):
                    alternatives[(i, i2)] = alternatives[(i + 1, i2)]
                    results[(i, i2)] = results[(i + 1, i2)]
        del questions[-1]
        del amount_of_alternatives[-1]
        del index[-1]
    else:
        return

    db['index'] = index
    db['questions'] = questions
    db['amount_of_alternatives'] = amount_of_alternatives
    db['results'] = results
    db['alternatives'] = alternatives
    return

# -----------------------------------------------------------------------------------

def generate_database():  # generates a database file with a generic question.
    db = DBProxy(databasename)

    index = []
    index.append(0)
    indexcounter = 0

    questions = []
    questions.append('Which is your prefered BBS software?')

    alternatives = {}
    alternatives[(0, 0)] = 'X/84'
    alternatives[(0, 1)] = 'Daydream'
    alternatives[(0, 2)] = 'Mystic'
    alternatives[(0, 3)] = 'Synchronet'
    alternatives[(0, 4)] = 'ENiGMA½'

    results = {}
    results[(0, 0)] = 0
    results[(0, 1)] = 0
    results[(0, 2)] = 0
    results[(0, 3)] = 0
    results[(0, 4)] = 0

    amount_of_alternatives = []
    # this is the only list/dict that is not zerobased..
    amount_of_alternatives.append(4)

    db['indexcounter'] = indexcounter
    db['index'] = index
    db['amount_of_alternatives'] = amount_of_alternatives
    db['alternatives'] = alternatives
    db['results'] = results
    db['questions'] = questions

# -----------------------------------------------------------------------------------

def main():
    session = getsession()
    session.activity = 'hanging out in voting script'
    term = getterminal()
    echo(syncterm_setfont('topaz'))

    db = DBProxy(databasename)
    if 'questions' not in db:
        generate_database()

    while True:
        # clears the screen and displays the vote art header
        echo(term.clear())
        for line in showart(
                os.path.join(os.path.dirname(__file__), 'art', 'vote.ans'), 'cp437'):
            echo(term.cyan + term.move_x(max(0, (term.width / 2) - 40)) + line)

        if 'sysop' in session.user.groups:
            spacing = 1
        else:
            spacing = 7
            echo(' ')
        echo(term.magenta('\n (') + term.cyan('r') + term.magenta(')') +
             term.white('esults') + ' ' * spacing +
             term.magenta('(') + term.cyan('v') + term.magenta(')') +
             term.white('ote on a question') + ' ' * spacing +
             term.magenta('(') + term.cyan('a') + term.magenta(')') +
             term.white('dd a new question') + ' ' * spacing)
        if 'sysop' in session.user.groups:
            echo(term.magenta('(') + term.cyan('d') + term.magenta(')') +
                 term.white('elete a question') + ' ' * spacing)
        echo(term.magenta('(') + term.cyan('q') + term.magenta(')') + term.white('uit') +
             term.magenta('\r\n\r\nx/84 voting booth command: '))
        le = LineEditor(10)
        le.colors['highlight'] = term.cyan
        inp = le.read()
        # makes the input indifferent to wheter you used lower case when typing
        # in a command or not..
        inp = (inp or '').lower()

        if 'sysop' in session.user.groups and inp == 'd':
            while True:
                questionnumber = query_question()
                if questionnumber == -1:
                    break
                delete_question(questionnumber)
        elif inp == 'r':
            while True:
                questionnumber = query_question()
                if questionnumber == -1:
                    break
                list_results(questionnumber)
        elif inp == 'v':
            while True:
                questionnumber = query_question()
                if questionnumber == -1:
                    break
                vote(questionnumber)
        elif inp == 'a':
            add_question()
        elif inp == 'q':
            return
        else:
            # if no valid key is pressed then do some ami/x esthetics.
            echo(term.red('\r\nNo such command. Try again.\r\n'))
            waitprompt(term)
