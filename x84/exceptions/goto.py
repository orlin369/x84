#!/usr/bin/env python
# -*- coding: utf8 -*-
 
""" Custom exceptions for x/84. """

from bbs.script_def import Script

class Goto(Exception):

    """ Thrown to change script without returning. """

    def __init__(self, script, *args, **kwargs):

        self.value = Script(name=script, args=args, kwargs=kwargs)
