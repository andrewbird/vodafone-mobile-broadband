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
All the exceptions in VMCCdfL
"""
__version__ = "$Rev: 1172 $"

class VMCError(Exception):
    """
    Base class of all VMC errors
    """

class AlreadyConnected(VMCError):
    """
    Raised when the user tries to connect to Internet and is already connected
    """

class AlreadyConnecting(VMCError):
    """
    Raised when the user tries to connect to Internet and is in the middle of
    the process of connecting
    """

class AlreadyTrackingError(VMCError):
    """
    Raised when the tracker is initialized twice
    """

class NotTrackingError(VMCError):
    """
    Raised when something is trying to request data from a tracker
    """

class ATError(VMCError):
    """Exception raised when an ERROR has occurred"""

class ATTimeout(VMCError):
    """
    Exception raised when the timeout specified for the given C{ATCmd} expired
    """

class AuthCancelled(VMCError):
    """Exception raised when user cancels the authentication"""

class CharsetError(VMCError):
    """
    Exception raised when VMC can't find an appropriate charset at startup
    """

class CMEError(VMCError):
    """Exception raised when a CME ERROR has occurred"""

class CMEErrorIncorrectPassword(CMEError):
    """Exception raised with a +CME ERROR: incorrect password"""

class CMEErrorInvalidCharactersInDialString(CMEError):
    """
    Exception raised with a +CME ERROR: invalid characters in dial string
    """

class CMEErrorNoNetworkService(CMEError):
    """
    Exception raised with a +CME ERROR: no network service
    """

class CMEErrorNotFound(CMEError):
    """Exception raised with a +CME ERROR: not found"""

class CMEErrorOperationNotAllowed(CMEError):
    """Exception raised with a +CME ERROR: operation not allowed"""

class CMEErrorStringTooLong(CMEError):
    """Exception raised with a +CME ERROR: string too long"""

class CMEErrorSIMBusy(CMEError):
    """Exception raised with a +CME ERROR: SIM busy"""

class CMEErrorSIMFailure(CMEError):
    """Exception raised with a +CME ERROR: SIM failure"""

class CMEErrorSIMNotStarted(CMEError):
    """Exception raised with +CME ERROR: SIM interface not started"""

class CMEErrorSIMNotInserted(CMEError):
    """Exception raised with +CME ERROR: SIM not inserted"""

class CMEErrorSIMPINRequired(CMEError):
    """Exception raised with +CME ERROR: SIM PIN required"""

class CMEErrorSIMPUKRequired(CMEError):
    """Exception raised with +CME ERROR: SIM PUK required"""

class CMEErrorSIMPUK2Required(CMEError):
    """Exception raised with +CME ERROR: SIM PUK2 required"""

class CMSError(Exception):
    """Base class for CMS errors"""

class CMSError300(CMSError):
    """CMS ERROR: Phone failure"""

class CMSError301(CMSError):
    """CMS ERROR: SMS service of phone reserved """

class CMSError302(CMSError):
    """CMS ERROR: Operation not allowed"""

class CMSError303(CMSError):
    """CMS ERROR: Operation not supported"""

class CMSError304(CMSError):
    """CMS ERROR: Invalid PDU mode parameter"""

class CMSError305(CMSError):
    """CMS ERROR: Invalid text mode parameter"""

class CMSError310(CMSError):
    """CMS ERROR: SIM not inserted"""

class CMSError311(CMSError):
    """CMS ERROR: SIM PIN necessary"""

class CMSError313(CMSError):
    """CMS ERROR: SIM failure"""

class CMSError314(CMSError):
    """CMS ERROR: SIM busy"""

class CMSError315(CMSError):
    """CMS ERROR: SIM wrong"""

class CMSError320(CMSError):
    """CMS ERROR: Memory failure"""

class CMSError321(CMSError):
    """CMS ERROR: Invalid memory index"""

class CMSError322(CMSError):
    """CMS ERROR: Memory full"""

class CMSError330(CMSError):
    """CMS ERROR: SMSC address unknown"""

class CMSError331(CMSError):
    """CMS ERROR: No network service"""

class CMSError332(CMSError):
    """CMS ERROR: Network timeout"""

class CMSError500(CMSError):
    """CMS ERROR: Unknown Error"""

class DeviceNotFoundError(VMCError):
    """Exception raised when no suitable device has been found"""

class DeviceLacksExtractInfo(VMCError):
    """
    Exception raised when no control ports nor data ports have been extracted
    """

class DeviceLocked(VMCError):
    """
    Exception raised after an authentication mess ending up in a device locked
    """

class IllegalOperationError(VMCError):
    """
    Raised on single port devices that try to execute command while connected
    """

class InputValueError(VMCError):
    """Exception raised when INPUT VALUE IS OUT OF RANGE is received"""

class MalformedSMSError(VMCError):
    """Exception raised when an error is received decodifying a SMS"""

class NetworkRegistrationError(VMCError):
    """
    Exception raised when an error occurred while registering with the network
    """

class NetworkTemporalyUnavailableError(VMCError):
    """
    Exception raised when the network we are registered with its not available
    """

class NotConnectedError(VMCError):
    """Exception raised when we are not connected and try to disconnect"""

class OSNotRegisteredError(VMCError):
    """Exception raised when the current OS is not registered"""

class PluginDependenciesError(VMCError):
    """Exception raised when plugin's dependencies are unmet"""

class PluginInitializationError(VMCError):
    """Exception raised when an error ocurred initing the plugin"""

class ProfileNotFoundError(VMCError):
    """Exception raised when a profile hasn't been found"""

class ProfileInUseError(VMCError):
    """Exception raised when user tries to delete the active profile"""

class StateMachineNotReadyError(VMCError):
    """
    Raised when a third-party developer tries to obtain a reference to the
    state machine too soon
    """

class UnknownPluginNameError(VMCError):
    """
    Exception raised when we don't have a plugin with the given remote name
    """
