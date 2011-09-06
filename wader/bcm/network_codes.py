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

    # VF-NL
    ('20404', '*#100#', '(?P<number>\+?\d+)'),

    # VF-ES
    ('21401', '*138#', '(?P<number>\+?\d+)'),

    # VF-Switzerland
    ('22801', '*#100#', '(?P<number>\+?\d+)'),

    # VF-UK(confirmed)
    ('23415', '*#100#', '(?P<number>\+?\d+)'),

    # Cytamobile(confirmed)
    # '+35797732112'
    ('28001', '#109#', '(?P<number>\+?\d+)'),

    # VF-TR MVNO
    ('2860251', '#99#', '(?P<number>\+?\d+)'),

    # VF-TR
    ('28602', '*101#', '(?P<number>\+?\d+)'),

    # VF-Faroe Islands
    ('28802', '*#100#', '(?P<number>\+?\d+)'),

    # VF-Slovenia
    ('29340', '*100#', '(?P<number>\+?\d+)'),

    # VF-Azerbaijan
    ('40004', '*100#3#', '(?P<number>\+?\d+)'),

    # VF-Dubai
    ('42403', '*#100#', '(?P<number>\+?\d+)'),

    # VF-Qatar
    ('42702', '*#100#', '(?P<number>\+?\d+)'),

    # VF-Fiji MVNO
    ('5420171', '*124*1*4#', '(?P<number>\+?\d+)'),

    # VF-Fiji
    ('54201', '*999#', '(?P<number>\+?\d+)'),

    # VF-Egypt
    ('60202', '*878#', 'Mobile Number is (?P<number>\+?\d+)'),

    # VF-Ghana
    ('62002', '*127#', '(?P<number>\+?\d+)'),

    # VF-South Africa
    ('65501', '*111*501#', '(?P<number>\+?\d+)'),

    # MTN SA(confirmed)
    # result == 'Yello! Your MSISDN is 073583xxxx'
    #('65510', '*131*3#', '(?P<number>\+?\d+)'),    # national
    # result == 'Yello! Your MSISDN is 2773583xxxx'
    ('65510', '*123*888#', '(?P<number>\+?\d+)'),  # international
]

PAYT_CREDIT_CHECK_USSD = [
    # mccmnc, balance request, extract value regex, display currency format

    # VF-NL
    ('20404', '*101#', '.*?(?P<value>\d+\.\d\d).*?', '€%s'),

    # VF-ES
    ('21401', '*134#', '.*?(?P<value>\d+\.\d\d).*?', '€%s'),

    # VF-UK(confirmed)
    ('23415', '*#135#', '.*?(?P<value>\d+\.\d\d).*?', '£%s'),

    # Cytamobile(confirmed)
    # 'Your balance is 5.00 EUR and your top-up validity period expires on'
    # ' 26 Jun 2011.'
    ('28001', '*110#', '.*?(?P<value>\d+\.\d\d).*?', '€%s'),

    # VF-TR
    ('28602', '*123#', '.*?(?P<value>[\d\.,]+).*?', '%sTL'),

    # VF-Slovenia
    ('29340', '*448#', '(?P<value>.*)', '%s'),

    # VF-Azerbaijan
    ('40004', '*100#', '(?P<value>.*)', '%s'),

    # VF-Fiji
    ('54201', '*131#', '(?P<value>.*)', '%s'),

    # VF-Egypt
    ('60202', '*868*1#', '(?P<value>.*)', '%s'),

    # VF-Ghana
    ('62002', '*122#', '(?P<value>.*)', '%s'),

    # Zain Kenya
    ('63903', '*133#', '.*?(?P<value>\d+\.\d\d).*?', 'KES%s'),

    # Vodacom SA(confirmed)
    ('65501', '*100#', '.*?(?P<value>\d+\.\d\d).*?', 'R%s'),

    # CellC SA
    ('65507', '*101#', '.*?(?P<value>\d+\.\d\d).*?', 'R%s'),

    # MTN SA (confirmed)
    # result == "Y'ello, you have\nR6.29 airtime \n0 SMS(s) and\n"
    #           "4.20 MB data.\nYou are on MTN Zone. Please dial *141*1# "
    #           "for detailed balances.\nBrought to you by MTN."
    ('65510', '*141#', '.*?(?P<value>\d+\.\d\d).*?', 'R%s'),

    # Chile
    ('73001', '*#1345#', '.*?(?P<value>\d+\.?\d\d).*?', '$%s'),
]

PAYT_SUBMIT_VOUCHER_USSD = [
    # mccmnc, submit request, success regex

    # VF-NL
    ('20404', '*#1345*%s#', '.*?(?P<success>geslaagd).*?'),

    # VF-ES
    ('21401', '*133*%s#', '.*?(?P<success>activado).*?'),

    # VF-UK(confirmed)
    ('23415', '*#1345*%s#', '.*?(?P<success>TopUp successful).*?'),

    # Cytamobile(not tested yet, but according to leaflet they are 16 digits)
    ('28001', '*116*%s#', '.*?(?P<success>Thank you).*?'),

    # VF-TR TopUp is really wild and not supported by the UI so left out

    # VF-Slovenia
    ('29340', '*448*HRN#%s#', '.*?(?P<success>novo stanje).*?'),

    # VF-Azerbaijan
    ('40004', '*111#%s#',
        '.*?(?P<success>Yüklənmə müvəffəqiyyətlə həyata keçirildi).*?'),

    # VF-Fiji
    ('54201', '*132*%s#', '.*?(?P<success>Recharge successful).*?'),

    # VF-Egypt
    ('60202', '*858*%s#', '.*?(?P<success>successful).*?'),

    # VF-Ghana
    ('62002', '*126#%s#', '.*?(?P<success>Your credit is).*?'),

    # Zain Kenya(guessed)
    ('63903', '*122*%s#',
        '.*?(?P<success>please report this USSD string to betavine).*?'),

    # Vodacom SA(confirmed)
    # success == 'Recharged: 29.00 NewBalance: 29.00 Points earned: 3.'
    ('65501', '*100*01*%s#',
        '^[Rr]echarged:\s*(?P<success>(?:\d{2,}|[1-9])\.\d\d)'),

    # CellC SA
    # success == 'Recharged = R 25.00 . Balance = R 25.01'
    ('65507', '*102*%s#',
        '^Recharged\s*=\s*R\s*(?P<success>(?:\d{2,}|[1-9])\.\d\d)\s*'),

    # MTN SA
    # success == 'Your account has been recharged with R30.00 airtime
    #             Brought to you by MTN.'
    ('65510', '*141*%s#',
        'recharged with R\s*(?P<success>(?:\d{2,}|[1-9])\.\d\d)\s*airtime'),

    # Chile
    ('73001', '*#1345*%s#', '.*?(?P<success>exitoso).*?'),
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
    ('20810', '4357', '+33 6 1000 4357'),  # SFR
    ('21401', '123', '+34 607 123 000'),   # VF-ES
    ('22210', '190', None),                # VF-IT
    ('23415', '191', '+44 870 070 0191'),  # VF-UK
    ('26202', '1212', '+49 172 1212'),     # VF-DE
    ('28001', '132', None),                # Cytamobile-Vodafone
    ('65501', '100', '+27 82 100'),        # Vodacom SA (very likely)
    ('65507', '140', '+27 84 140'),        # Cell C SA (confirmed)
    ('65510', '173', '+27 83 173'),        # MTN SA (confirmed)
]


def get_customer_support_info(imsi):
    for net in CUSTOMER_SUPPORT_NUMBERS:
        if imsi.startswith(net[0]):
            return net[1:]
    return None
