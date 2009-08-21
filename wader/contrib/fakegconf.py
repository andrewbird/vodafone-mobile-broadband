# -*- coding: utf-8 -*-
# Copyright (c) 2006 Jani Monoses  <jani@ubuntu.com>
# Copyright (C) 2006-2007  Vodafone España, S.A.
# Authors: Jani Monoses, Pablo Martí
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


# This is a class which handles settings when the gconf library
# is unavailable such as in a non-Gnome environment
# The configuration is stored in python hash format which is sourced
# at program start and dumped at exit

# Modified for Vodafone Mobile Connect Card driver for Linux by
# Pablo Martí on 11 August 2007
# log:
#   * modified the CONFIG_FILE PATH to suit VMC's schema
#   * this file is part of Ubuntu's UpdateManager, the file didn't have
#     a license, but UpdateManager is released under the GPL. I've attached
#     the GPL to the file and credit is given to the original author
# Pablo Martí on 31 August 2007
# log:
#   * Added set_int and get_int functions

import string
import atexit
import os.path

from wader.common.consts import FAKE_GCONF

class FakeGconf(object):
    def __init__(self, fakepath=FAKE_GCONF):
        self.CONFIG_FILE = os.path.expanduser(fakepath)
        self.config = {}
        try:
            #execute python file which contains the dictionary called config
            exec open (self.CONFIG_FILE)
            self.config = config
        except:
            pass

    #only get the 'basename' from the gconf key
    def keyname(self, key):
        return string.rsplit(key, '/', 1)[-1]

    def get_bool(self, key):
        key = self.keyname(key)
        return self.config.setdefault(self.keyname(key), True)

    def set_bool(self, key, value):
        key = self.keyname(key)
        self.config[key] = value

    def set_int(self, key, value):
        key = self.keyname(key)
        self.config[key] = value

    def get_int(self, key):
        return self.config.setdefault(self.keyname(key), 0)

    def get_string(self, key):
        key = self.keyname(key)
        return self.config.setdefault(self.keyname(key), "")

    def set_string(self, key, value):
        key = self.keyname(key)
        self.config[key] = value

    # FIXME assume type is int for now
    def get_pair(self, key, ta=None, tb=None):
        key = self.keyname(key)
        return self.config.setdefault(self.keyname(key), [400, 500])

    # FIXME assume type is int for now
    def set_pair(self, key, ta, tb, a, b):
        key = self.keyname(key)
        self.config[key] = [a, b]

    #Save current dictionary to config file
    def save(self):
        file = open(self.CONFIG_FILE, "w")
        data = "config = {"
        for i in self.config:
            data +=  "'"+i+"'" + ":" + str(self.config[i])+",\n"
        data += "}"
        file.write(data)
        file.close()


VALUE_INT = ""

fakegconf = FakeGconf()

def client_get_default():
    return fakegconf

def fakegconf_atexit():
    fakegconf.save()

atexit.register(fakegconf_atexit)

