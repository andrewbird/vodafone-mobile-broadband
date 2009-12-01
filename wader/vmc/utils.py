# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  Jaime Soriano
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

UNIT_B, UNIT_KB, UNIT_MB, UNIT_GB = xrange(4)
UNIT_REPR = {
    UNIT_B:  "B",
    UNIT_KB: "KB",
    UNIT_MB: "MB",
    UNIT_GB: "GB",
}


def get_error_msg(e):
    """
    Returns the message attributte of ``e``
    """
    if hasattr(e, 'get_dbus_name'):
        return e.get_dbus_name()

    return e.message


def dbus_error_is(e, exception):
    return exception.__name__ in get_error_msg(e)


def units_to_bits(value, units):
    return value * 8 * (2 ** (units * 10))


def units_to_bytes(value, units):
    return value * (2 ** (units * 10))


def bits_to_units(bits, units):
    _bytes = (bits / 8)
    return float(_bytes) / (2 ** (units * 10))


def bytes_to_units(_bytes, units):
    return float(_bytes) / (2 ** (units * 10))


def repr_usage(_bytes, units=None, _round=None):
    if _round is None:
        _round = lambda x: int(x)

    if not units:
        if _bytes == 0:
            units = UNIT_B
        else:
            units = UNIT_GB
            for u in [UNIT_B, UNIT_KB, UNIT_MB, UNIT_GB]:
                btu = bytes_to_units(_bytes, u)
                if btu >= 1 and btu < 10:
                    units = u -1
                    break
                elif btu >= 10 and btu < 1024:
                    units = u
                    break
    while _bytes > 0 and bytes_to_units(_bytes, units) < 1 and units > UNIT_B:
        units -= 1
    return "%d%s" % (_round(bytes_to_units(_bytes, units)), UNIT_REPR[units])


def bytes_repr(_bytes):
    return repr_usage(_bytes)
