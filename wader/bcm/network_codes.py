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
    # mccmnc, msisdn request, extract number regex
    ('20404', '*#100#', '(?P<number>\+?\d+)'), # VF-NL
    ('23415', '*#100#', '(?P<number>\+?\d+)'), # VF-UK
    ('28000', '#109#', '(?P<number>\+?\d+)'),  # Cytamobile
]

PAYT_CREDIT_CHECK_USSD = [
    # mccmnc, balance request, extract value regex, display currency format
    ('20404', '*101#', '.*?(?P<value>\d+\.\d\d).*?', '€%s'),    # VF-NL
    ('23415', '*#135#', '.*?(?P<value>\d+\.\d\d).*?', '£%s'),   # VF-UK
    ('28000', '*110#', '.*?(?P<value>\d+\.\d\d).*?', '€%s'),    # Cytamobile
    ('65501', '*111*500#', '.*?(?P<value>\d+\.\d\d).*?', 'R%s'),# Vodacom SA
    ('73001', '*#1345#', '.*?(?P<value>\d+\.?\d\d).*?', '$%s'), # Chile
]

PAYT_SUBMIT_VOUCHER_USSD = [
    # mccmnc, submit request, success regex
    ('20404', '*#1345*%s#', '.*?(?P<success>geslaagd).*?'),         # VF-NL(guessed)
    ('23415', '*#1345*%s#', '.*?(?P<success>TopUp successful).*?'), # VF-UK
    ('28000', '*116*%s#', '.*?(?P<success>επιτυχής).*?'),           # Cytamobile(guessed)
    ('65501', '*111*501#%s#', '.*?(?P<success>suksesvolle).*?'),    # Vodacom SA(guessed)
    ('73001', '*#1345*%s#', '.*?(?P<success>exitoso).*?'),          # Chile(guessed)
]


def get_ussd_info(imsi, info):
    for net in info:
        if imsi.startswith(net[0]):
            return net
    return None


def get_msisdn_ussd_info(imsi):
    return get_ussd_info(imsi, MSISDN_USSD)


def get_payt_credit_check_info(imsi):
    return get_ussd_info(imsi, PAYT_CREDIT_CHECK_USSD)


def get_payt_submit_voucher_info(imsi):
    return get_ussd_info(imsi, PAYT_SUBMIT_VOUCHER_USSD)


CUSTOMER_SUPPORT_NUMBERS = [
    # mccmnc, shortcode, international
    ('20810', '4357', '+33 6 1000 4357'), # SFR
    ('21401', '123', '+34 607 123 000'),  # VF-ES
    ('22210', '190', None),               # VF-IT
    ('23415', '191', '+44 870 070 0191'), # VF-UK
    ('26202', '1212', '+49 172 1212'),    # VF-DE
]


def get_customer_support_info(imsi):
    for net in CUSTOMER_SUPPORT_NUMBERS:
        if imsi.startswith(net[0]):
            return net[1:]
    return None
