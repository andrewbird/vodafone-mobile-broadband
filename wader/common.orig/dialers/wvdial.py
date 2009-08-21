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
WVdial Dialer
"""
__version__ = "$Rev: 1189 $"

from cStringIO import StringIO
import errno
import os
import re
import stat
import shutil
from string import Template
import tempfile

from twisted.python import log, procutils
from twisted.internet import utils, reactor, defer, protocol

import wader.common.consts as consts
from wader.common.encoding import _
from wader.common.dialer import Dialer, DialerConf
import wader.common.notifications as N
from vmc.utils.utilities import get_file_data, save_file, is_bogus_ip
from vmc.contrib import louie

PAP_SECRETS = os.path.join(consts.TOP_DIR, 'etc', 'ppp', 'pap-secrets')
CHAP_SECRETS = os.path.join(consts.TOP_DIR, 'etc', 'ppp', 'chap-secrets')

### wvdial.conf stuff
def get_wvdial_conf_file(conf, serial_port):
    """Returns the path of the generated wvdial.conf"""
    text = _generate_wvdial_conf(conf, serial_port)
    dirpath = tempfile.mkdtemp('', 'VMC', '/tmp')
    filepath = tempfile.mkstemp('wvdial.conf', 'VMC', dirpath, True)[1]
    save_file(filepath, text)
    return filepath

def _generate_wvdial_conf(conf, sport):
    """
    Generates a specially crafted wvdial.conf with the given serial_port
    """
    if len(conf.username) > 0: # Wvdial doesn't like empty assignments
        user = conf.username
    else:
        user = '*'

    if len(conf.password) > 0:
        passwd = conf.password
    else:
        passwd = '*'

    if conf.staticdns:
        autodns = 'Off'
    else:
        autodns = 'On'

    theapn = conf.apn_host

    # build template
    data = StringIO(get_file_data(consts.WVTEMPLATE))
    template = Template(data.getvalue())
    data.close()
    # return template
    opts = dict(serialport=sport, username=user, password=passwd, apn=theapn, autodns=autodns)
    return template.substitute(opts)


class WvdialProfile(object):
    """I represent a custom wvdial profile"""
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self._directives = [line.replace('\n', '') for line
                                in open(self.path).readlines()]

    def serialise(self):
        fobj = open(self.path, 'w')
        for directive in self._directives:
            fobj.write(directive + '\n')

        fobj.close()

    def has_key(self, key):
        if key in self._directives:
            return True
        return False

    def remove_key(self, key):
        if self.has_key(key):
            self._directives.remove(key)

def get_profile_from_name(name):
    """Returns a C{WvdialProfile} object corresponding to profile c{name}"""
    path = os.path.join(consts.DIALER_PROFILES, name)
    return os.path.exists(path) and WvdialProfile(path) or None

def current_profile_uses_passwordplugin():
    """
    Returns True if current profile uses the passwordfd directive

    Since 0.9.7, VMCCdfL manages itself /etc/ppp/{ch,p}ap-secrets and using
    this directive is not supported on most distros
    """
    from wader.common.config import config
    key = config.current_profile.get('connection', 'dialer_profile')
    profile = get_profile_from_name(key)
    return profile.has_key('plugin passwordfd.so')

class SecretsEntry(object):
    """
    I represent an entry in /etc/ppp/{ch,p}ap-secrets
    """
    def __init__(self, user, host, password, ip=None):
        self.user = user
        self.host = host
        self.password = password
        self.ip = ip

    def __eq__(self, entry):
        if self.user == entry.user and self.host == entry.host \
                    and self.password == self.password:
            try:
                if self.ip == entry.ip:
                    return True
                return False
            except NameError:
                return True

        return False

    def to_csv(self):
        if not self.ip:
            return '"%s"\t%s\t"%s"\n' % (self.user, self.host, self.password)
        else:
            return '"%s"\t%s\t"%s"\t%s\n' % (self.user, self.host,
                                           self.password, self.ip)


def append_username_passwd_to_secret(path, entry):
    # read contents
    lines = open(path).readlines()
    entries = extract_entries_from_lines(lines)

    if entry not in entries:
        # now paste contents back and we might add something
        fobj = open(path, 'w')
        fobj.writelines(lines)
        fobj.write(entry.to_csv())
        fobj.close()

def extract_entries_from_lines(lines):
    pattern = re.compile(r"""
            "?(?P<user>\S+)"?
            \t\*\t
            "?(?P<passwd>\S+)"?
            """, re.VERBOSE | re.M)
    response = []
    for line in lines:
        match = pattern.match(line)
        if match:
            user, passwd = match.groups()
            if user[-1] == '"':
                user = user[:-1]
            response.append(SecretsEntry(user, '*', passwd))

    return response

def append_entry_to_secrets(username, password,
                             pap_path=PAP_SECRETS, chap_path=CHAP_SECRETS):
    entry = SecretsEntry(username, '*', password)
    append_username_passwd_to_secret(pap_path, entry)
    append_username_passwd_to_secret(chap_path, entry)

def setup_secrets():
    """Appends a new entry to /etc/ppp/{ch,p}ap-secrets"""
    # get username and password
    from wader.common.config import config
    username = config.current_profile.get('connection', 'username')
    password = config.current_profile.get('connection', 'password')
    #setup secrets
    append_entry_to_secrets(username, password)

def setup_secrets_cli(_config):
    username = _config['username']
    password = _config['password']
    #setup secrets
    append_entry_to_secrets(username, password)


class WvdialDialer(Dialer):
    """
    Dialer for Wvdial
    """
    binary = 'wvdial'

    def __init__(self):
        super(WvdialDialer, self).__init__()
        self.bin_path = procutils.which(self.binary)[0]
        self.dialconf = None
        self.conf_path = ""
        self.proto = None
        self.iconn = None

    def check_assumptions(self):
        from wader.common.oal import osobj
        if osobj.manage_secrets:
            if current_profile_uses_passwordplugin():
                message = _("WVDial directive error")
                details = _("""
Since version 0.9.7 %s manages pppd's /etc/ppp/{p,ch}ap-secrets, the
'plugin passwordfd.so' directive should not appear on the
current wvdial profile, please remove it manually. Go to
Tools -> Preferences, select the wvdial profiles tab, and
remove from the current wvdial profile the
'plugin passwordfd.so' line.""") % consts.APP_LONG_NAME
                return message, details

        return None

    def check_permissions(self):
        import grp
        import pwd
        from wader.common.oal import osobj

        array = [(PAP_SECRETS, 0660),
                 (CHAP_SECRETS, 0660),
        ]

        response = []
        for (path, permissions) in array:
            st = os.stat(path)
            mode = stat.S_IMODE(os.stat(path)[stat.ST_MODE])
            if permissions != mode:
                args = (path, permissions, mode)
                msg = "%s should have 0%03o mode, found 0%03o" % args
                response.append(msg)

        # now check /etc/ppp/peers permissions
        peerspath = os.path.dirname(os.path.join(consts.TOP_DIR, 'etc',
                                     'ppp', 'peers', 'wvdial'))
        if not os.access(peerspath, os.W_OK | os.R_OK):
            # the os.access call fails on a unionfs (Feisty Live)
            # opening a file in write mode in /etc/ppp/peers also fails, instead
            # we create a file in /tmp and try to copy it to /etc/ppp/peers if
            # that doesn't fails that means we're on a LiveCD with unionfs
            tmp_path = os.path.join('/tmp', 'foo.bar')
            fobj = open(tmp_path, 'w')
            dirname = os.path.dirname(osobj.abstraction['WVDIAL_AUTH_CONF'])
            finalpath = os.path.join(dirname, 'foo.bar')
            try:
                shutil.copy(tmp_path, finalpath)
            except IOError, e:
                if e.errno == errno.EACCES:
                    pass
                else:
                    raise
            else:
                # oh you tricky unionfs
                # cleanup trash left
                os.unlink(finalpath)
                return response

            gid = os.stat(peerspath).st_gid
            groupinfo = grp.getgrgid(gid)
            msg = '%s should be readable and writtable by group %s'
            response.append(msg % (peerspath, groupinfo[0]))
            uid = os.geteuid()
            userinfo = pwd.getpwuid(uid)
            username = userinfo[0]
            if username not in groupinfo.gr_mem:
                args = (username, groupinfo[0])
                msg = 'user %s should be a member of group %s' % args
                response.append(msg)

        return response

    def configure(self, dialconf, device):
        from wader.common.config import config
        if config.getboolean('preferences', 'manage_secrets'):
            setup_secrets()

        self._generate_config(dialconf, device)

    def configure_from_profile(self, profile, device):
        # generate the configuration
        dialconf = DialerConf.from_profile(profile)
        self.configure(dialconf, device)

    def connect(self):
        # get the args necessary to start wvdial on this distro
        from wader.common.oal import osobj
        args = osobj.get_connection_args(self)

        self.proto = WVDialProtocol(self.dialconf.staticdns)
        self.iconn = reactor.spawnProcess(self.proto, args[0], args, env=None)
        return self.proto.deferred

    def disconnect(self):
        # get disconnection arguments
        from wader.common.oal import osobj
        args = osobj.get_disconnection_args(self)
        # ignore the fact that we are gonna be disconnected
        self.proto.ignore_disconnect = True
        d = utils.getProcessValue(args[0], args, env=None)
        def disconnect_cb(error_code):
            log.err("EXIT CODE %d" % error_code)
            self._cleanup()
            return defer.succeed(True)

        d.addCallback(disconnect_cb)
        d.addErrback(lambda failure: log.err(failure))
        return d

    def _generate_config(self, dialconf, device):

        # generate wvdial.conf from template
        self.conf_path = get_wvdial_conf_file(dialconf, device.dport)

        self.dialconf = dialconf
        # generate DNS lock if necessary
        if self.dialconf.staticdns:
            from vmc.utils.utilities import generate_vmc_dns_lock
            generate_vmc_dns_lock(self.dialconf.dns1, self.dialconf.dns2)

        # create profile in /etc/ppp/peers/wvdial
        from wader.common.oal import osobj # plugin retrieval taken from beta 3
        data = osobj.get_config_template(self.dialconf.dialer_profile)
        try:
            os.unlink(consts.WVDIAL_AUTH_CONF)
        except OSError:
            # /etc/ppp/peers/wvdial could not exist
            pass
        save_file(consts.WVDIAL_AUTH_CONF, data)


    def _cleanup(self):
        """cleanup our traces"""
        try:
            path = os.path.dirname(self.conf_path)
            os.unlink(self.conf_path)
            os.rmdir(path)
        except (IOError, OSError):
            pass

        if self.dialconf.staticdns:
            # remove the dns lock
            try:
                os.unlink(consts.VMC_DNS_LOCK)
            except (IOError, OSError):
                pass


MAX_ATTEMPTS_REGEXP = re.compile('Maximum Attempts Exceeded')
PPPD_DIED_REGEXP = re.compile('The PPP daemon has died')
AUTH_SUCCESS_REGEXP = re.compile('Authentication.*(CHAP|PAP).*successful')
LOCAL_IP_SUCCESS_REGEXP = re.compile('local\s+IP\s+address\s+[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
DNS_REGEXP = re.compile(r"""
   DNS\saddress
   \s                                     # beginning of the string
   (?P<ip>                                # group named ip
   (25[0-5]|                              # integer range 250-255 OR
   2[0-4][0-9]|                           # integer range 200-249 OR
   [01]?[0-9][0-9]?)                      # any number < 200
   \.                                     # matches '.'
   (25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?) # repeat
   \.                                     # matches '.'
   (25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?) # repeat
   \.                                     # matches '.'
   (25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?) # repeat
   )                                      # end of group
   \b                                     # end of the string
   """, re.VERBOSE)

class WVDialProtocol(protocol.ProcessProtocol):
    """ProcessProtocol for wvdial"""

    def __init__(self, staticdns):
        self.__connected = False
        self.deferred = defer.Deferred()
        self.staticdns = staticdns
        self.ignore_disconnect = False
        self.dns = []

    def connectionMade(self):
        self.transport.closeStdin()

    def outReceived(self, data):
        log.msg("WVDIAL: sysout %s" % data)

    def errReceived(self, data):
        """wvdial has this bad habit of using stderr for debug"""
        log.msg('WVDIAL: DATA RECV %s' % data)
        self.parse_output(data)

    def outConnectionLost(self):
        log.msg('WVDIAL: pppd closed their stdout!')

    def errConnectionLost(self):
        log.msg('WVDIAL: pppd closed their stderr.')

    def processEnded(self, status_object):
        log.msg('WVDIAL: quitting')
        if not self.__connected:
            if not self.ignore_disconnect:
                louie.send(N.SIG_DISCONNECTED, None)

    def extract_connected(self, data):
        if self.__connected:
            return

        if LOCAL_IP_SUCCESS_REGEXP.search(data):
            # Notify the user we are connected
            louie.send(N.SIG_CONNECTED, None)
            self.deferred.callback(True)
            self.__connected = True

    def extract_dns_strings(self, data):
        if not self.staticdns: # check if they're valid DNS IPs only if she didn't specify static DNS
            for match in re.finditer(DNS_REGEXP, data):
                dns_ip = match.group('ip')
                self.dns.append(dns_ip)

            if len(self.dns) == 2:
                if is_bogus_ip(self.dns[0]) or is_bogus_ip(self.dns[1]):
                    # the DNS assigned by the APN is probably invalid
                    # let's notify the user
                    louie.send(N.SIG_INVALID_DNS, None, self.dns)

    def extract_disconnected(self, data):
        disconnected = MAX_ATTEMPTS_REGEXP.search(data)
        pppd_died = PPPD_DIED_REGEXP.search(data)
        if disconnected or pppd_died:
            if not self.ignore_disconnect:
                louie.send(N.SIG_DISCONNECTED, None)

    def parse_output(self, data):
        self.extract_connected(data)
        self.extract_dns_strings(data)
        self.extract_disconnected(data)

