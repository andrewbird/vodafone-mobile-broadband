# -*- coding: utf-8 -*-
# Copyright (C) 2010  Vodafone España, S.A.
# Author:  Andrew Bird
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

# Using list instead of dict because I want to preserve the order
# as some len(mcc+mnc) != 5
MSISDN_USSD = [
    ('20404', '*#100#', '(?P<number>\+?\d+)'), # VF-NL
    ('23415', '*#100#', '(?P<number>\+?\d+)'), # VF-UK
    ('28000', '#109#', '(?P<number>\+?\d+)'),  # Cytamobile
]

def get_msisdn_ussd_info(imsi):
    for net in MSISDN_USSD:
        if imsi.startswith(net[0]):
            return net
    return None

#Holland,
#UK
#Cyprus,
#SA,
#Chille
