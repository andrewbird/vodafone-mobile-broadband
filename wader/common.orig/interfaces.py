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
"""VMCCdfL interfaces"""

__version__ = "$Rev: 1172 $"

from zope.interface import Interface, Attribute

class IContact(Interface):
    """
    Interface that all contact backends must implement
    """

    def get_index():
        """Returns the contact's index"""

    def get_name():
        """Returns the contact's name"""

    def get_number():
        """Returns the contact's number"""

    def is_writable():
        """Returns the contact's writable status"""

    def external_editor():
        """Returns a list of cmd + args to edit the external contact or Null"""

    def image_16x16():
        """Returns the pathname of the 16x16 icon to represent this contact"""

    def to_csv():
        """Returns a csv string with the contact info"""

class IShortMessage(Interface):
    """
    Interface that all contact backends must implement
    """

    def get_number():
        """
        Returns the sender's number
        """

    def get_text():
        """
        Returns the message's text
        """

class ICollaborator(Interface):
    """
    ICollaborator aids AuthStateMachine providing necessary PIN/PUK/Whatever

    AuthStateMachine needs an object that provides ICollaborator in order to
    work. ICollaborator abstracts the mechanism through wich the PIN/PUK is
    obtained.
    """

    def get_pin():
        """Returns a C{Deferred} that will be callbacked with the PIN"""

    def get_puk():
        """
        Returns a C{Deferred} that will be cbcked with a (puk, sim) tuple
        """

    def get_puk2():
        """
        Returns a C{Deferred} that will be cbcked with a (puk2, sim) tuple
        """

class ICollaboratorFactory(Interface):
    def get_collaborator(self, device, view):
        """
        Returns an object implementing L{ICollaborator}

        @type device: L{wader.common.plugin.DevicePlugin}
        @param view: an optional parameter not used in CLI interfaces (or
        perhaps yes ;) Its a reference to a view that can be used to show
        progress of the authentication to the user.
        """

class IDialer(Interface):

    def check_assumptions():
        """
        Returns a list with all the assumptions not satisfied

        Its response is meant to be used as the input for an error dialog
        that will be shown at startup to inform about any potential errors or
        misconfigured files
        """

    def check_permissions():
        """
        Returns a list with all the permission problems

        Its response is meant to be used as the input for an error dialog
        that will be shown at startup to inform about any potential errors or
        misconfigured files
        """

    def configure(config, device):
        """
        Configures the dialer with C{config} for C{device}
        """

    def connect():
        """
        Returns a Deferred that will be callbacked when we connect to Internet
        """

    def disconnect():
        """
        Returns a Deferred that will be cbk'ed when we are disconnected
        """


class IVMCPlugin(Interface):
    """Base interface for all VMC plugins"""
    name = Attribute("""Plugin's name""")
    version = Attribute("""Plugin's version""")
    author = Attribute("""Plugin's author""")

    def initialize():
        """
        Initializes the plugin

        @raise wader.common.exceptions.PluginDependenciesError: Raised when the
        necessary dependencies are missing
        @raise wader.common.exceptions.PluginInitializationError:  Raised when
        an error ocurred while initalizing the plugin
        """

    def shutdown():
        """
        Closes the plugin
        """

class IDevicePlugin(IVMCPlugin):
    """Interface that all device plugins should implement"""
    baudrate = Attribute("""At which speed should we talk with this guy""")
    custom = Attribute("""Container with all the device's customizations""")
    sim = Attribute("""SIM object""")
    sconn = Attribute("""Reference to the serial connection instance""")

class IDBusDevicePlugin(IDevicePlugin):
    __properties__ = Attribute("""
            pairs of properties that must be satisfied by DBus backend""")

class IRemoteDevicePlugin(IDevicePlugin):
    """Interface that all remote device plugins should implent"""

    __remote_name__ = Attribute("""Response of an AT+CGMM command""")

class IOSPlugin(IVMCPlugin):
    distrib_id = Attribute("""Name of the OS/Distro""")
    distrib_version = Attribute("""Version of the OS/Distro""")

    abstraction = Attribute("""
        Dict with the 'abstraction_name, value' pairs""")
    customization = Attribute("""Dict with all the abstractions updates""")

    def check_dialer_assumptions():
        """
        Returns a message with whatever error happened configuring the dialer

        It returns a tuple of message, detail if something went wrong and
        returns None if every dialer assumption is met
        """

    def get_connection_args(wvdial_conf_path):
        """
        Returns the args necessary to start wvdial

        Some distributions ship with a setuid pppd, others don't. Thus
        what we return here will mainly depend on each distribution.
        """

    def get_disconnection_args():
        """
        Returns the args necessary to stop wvdial
        """

    def get_iface_stats(iface):
        """
        Returns a list with bits recv, sent for C{iface}
        """

    def get_timezone():
        """
        Returns the timezone of the OS

        @rtype: str
        """

    def get_tzinfo():
        """
        Returns a C{tzinfo} instance relative to the timezone

        @rtype: datetime.tzinfo
        """

    def is_valid():
        """Returns True if we are on the given OS/Distro"""


class INotificationPlugin(IVMCPlugin):
    klass = Attribute("""Class of the notification we are interested in""")

    def on_notification_received(wrapper, notification):
        """
        Called whenever a notification is received

        @type wrapper: L{wader.common.wrapper.BaseWrapper} subclass
        @type notification: wader.common.notifications.Notification

        Plugin developers should override this method
        """

class INotificationListener(Interface):
    def on_notification_received(notification):
        """
        Called whenever a notification is received

        @type notification: wader.common.notifications.Notification
        """
