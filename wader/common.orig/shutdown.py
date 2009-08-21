# -*- coding: utf-8 -*-
# Copyright (C) 2006-2007  Vodafone España, S.A.
# Author:  Pablo Martí
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
"""
Stuff used at shutdown
"""
__version__ = "$Rev: 1172 $"

from twisted.internet import reactor
from twisted.python import log

from wader.common.encoding import _

def shutdown_core(signal=None, frame=None, delay=2):
    from wader.common.config import config
    config.close() # free VMCConfig singleton

    from wader.common.phonebook import get_phonebook
    phonebook = get_phonebook(None)
    try:
        phonebook.close() # free Phonebook singleton
    except AttributeError:
        pass

    from wader.common.messages import get_messages_obj
    messages = get_messages_obj(None)
    try:
        messages.close() # free Messages singleton
    except AttributeError:
        pass

    from wader.common.persistent import net_manager
    try:
        net_manager.close()
    except AttributeError:
        pass

    log.msg(_('Shutting down...'))
    reactor.callLater(delay, reactor.stop)
