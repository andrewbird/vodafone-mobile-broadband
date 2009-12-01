# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
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

from math import ceil

from wader.vmc.translate import _

TIME_DESCRIPTION = {
    60 : 'minute',
    3600: 'hour',
    86400: 'day',
}

TIME_KEYS = TIME_DESCRIPTION.keys()
TIME_KEYS.sort()
TIME_KEYS.reverse()


def get_uptime():
    pf = open('/proc/uptime', 'r')
    if not pf:
        return ""

    uptime = pf.readline().rstrip()
    pf.close()

    if not len(uptime):
        return ""

    uptime = float(uptime.split()[0])
    uptime = int(ceil(uptime))
    return get_uptime_string(uptime)


def get_time_dict(uptime):
    """Returns a dictionary with a resolution of minutes"""
    resp = {}
    for key in TIME_KEYS:
        div = int(uptime / key)
        if div == 0:
            continue
        uptime -= div * key
        key_name = TIME_DESCRIPTION[key]
        resp[key_name] = div

    return resp


def get_uptime_string(uptime):
    """Returns a uptime(1)'s like output from a uptime expressed in seconds"""
    time_dict = get_time_dict(uptime)
    try:
        hour = "%d" % time_dict['hour']
    except KeyError:
        hour = "0"

    try:
        minute = "%d" % time_dict['minute']
        if time_dict['minute'] < 10:
            minute = '0' + minute
    except KeyError:
        minute = '00'

    msg = "%s:%s" % (hour, minute)
    try:
        day = time_dict['day']
        if day > 1:
            resp = _("%(day)d days, %(msg)s") % {'day': day, 'msg' : msg}
        else:
            resp = _("%(day)d day, %(msg)s") % {'day': day, 'msg' : msg}

    except KeyError:
        resp = msg

    return resp

if __name__ == '__main__':
    print get_uptime()
