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
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA..
"""Misc utilities"""

__version__ = '$Rev: 1172 $'

import re
import os
import subprocess

from wader.common.consts import VMC_DNS_LOCK

def natsort(l):
    """
    Naturally sort list C{l} in place
    """
    # extracted from http://nedbatchelder.com/blog/200712.html#e20071211T054956
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    l.sort(key=alphanum_key)

def run_lsb_cmd(cmd):
    def run_command(cmd):
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,)
        stdout_val = proc.communicate()[0]
        return stdout_val

    resp = run_command(cmd)
    val = resp.split('\t')[1]
    return val.replace('\n', '')

def extract_lsb_info():
    info = {}
    try:
        return dict(os_name=run_lsb_cmd('lsb_release -i'),
                    os_version=run_lsb_cmd('lsb_release -r'))

    except IndexError:
        return None

    return info

def dict_reverter(dict_in):
    """Returns a reverted copy of C{dict_in}"""
    dict_out = {}
    for k, v in dict_in.iteritems():
        dict_out[v] = k

    return dict_out

def touch(path):
    """
    Set the access/modified times of this file to the current time.

    Create the file if it does not exist.
    """
    # Borrowed from http://www.jorendorff.com/articles/python/path/src/path.py
    fd = os.open(path, os.O_WRONLY | os.O_CREAT, 0666)
    os.close(fd)
    os.utime(path, None)

def get_file_data(path):
    """Returns the data of the file at path C{path}"""
    if not os.path.exists(path):
        return None

    try:
        try:
            fileobj = open(path, 'r')
        except IOError:
            return None

        data = fileobj.read()
        return data
    finally:
        fileobj.close()

def save_file(path, data):
    """saves C{data} in C{path}"""
    try:
        fileobj = open(path, 'w')
        fileobj.write(data)
    finally:
        fileobj.close()

def generate_vmc_dns_lock(dns1, dns2, path=VMC_DNS_LOCK):
    """
    Generates a DNS lock for VMC in /tmp
    """
    text = "DNS1=" + dns1 + '\n'
    text += "DNS2=" + dns2 + '\n'
    save_file(path, text)

def is_bogus_ip(ip):
    """Returns True if C{ip} is a bogus ip"""
    return ip in ["10.11.12.13", "10.11.12.14"]

number_pattern = re.compile('^\+?\d+$')

def is_valid_number(number):
    return number_pattern.match(number) and True or False
