#  Author: Roberto Cavada <cavada@irst.itc.it>
#
#  Copyright (c) 2005 by Roberto Cavada
#
#  pygtkmvc is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2 of the License, or (at your option) any later version.
#
#  pygtkmvc is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free
#  Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
#  Boston, MA 02110, USA.
#
#  For more information on pygtkmvc see <http://pygtkmvc.sourceforge.net>
#  or email to the author Roberto Cavada <cavada@irst.itc.it>.
#  Please report bugs to <cavada@irst.itc.it>.

import support.metaclasses
from support.wrappers import ObsWrapperBase
from observable import Signal


class Model (object):
    """
    This class is the application model base class. It handles a set
    of observable properties which you are interested in showing by
    one or more views, via one or more observers of course. The
    mechanism is the following:

      1. You are interested in showing a set of model property, that
         you can declare in the __properties__ member map.

      2. You define one or more observers that observe one or more
         properties you registered. When someone changes a property
         value the model notifies the changing to each observer.

    The property-observer[s] association is given by the implicit
    rule in observers method names: if you want the model notified
    the changing event of the value of the property 'p' you have to
    define the method called 'property_p_value_change' in each
    listening observer class.

    Notice that typically 'controllers' implement the observer
    pattern. The notification method gets the emitting model, the
    old value for the property and the new one.  Properties
    functionalities are automatically provided by the
    ObservablePropertyMeta meta-class.
    """

    __metaclass__  = support.metaclasses.ObservablePropertyMeta
    __properties__ = {} # override this

    def __init__(self):
        object.__init__(self)
        self.__observers = []
        # keys are properties names, values are methods inside the observer:
        self.__value_notifications = {}
        self.__instance_notif_before = {}
        self.__instance_notif_after = {}
        self.__signal_notif = {}

        for key in (self.__properties__.keys() + self.__derived_properties__.keys()):
            self.register_property(key)

    def register_property(self, name):
        """Registers an existing property to be monitored, and sets
        up notifiers for notifications"""
        if not self.__value_notifications.has_key(name):
            self.__value_notifications[name] = []

        # registers observable wrappers
        prop = getattr(self, "_prop_%s" % name)

        if isinstance(prop, ObsWrapperBase):
            prop.__set_model__(self, name)

            if isinstance(prop, Signal):
                if not self.__signal_notif.has_key(name):
                    self.__signal_notif[name] = []
            else:
                if not self.__instance_notif_before.has_key(name):
                    self.__instance_notif_before[name] = []
                if not self.__instance_notif_after.has_key(name):
                    self.__instance_notif_after[name] = []

    def has_property(self, name):
        """Returns true if given property name refers an observable
        property inside self or inside derived classes"""
        return self.__properties__.has_key(name) or \
               self.__derived_properties__.has_key(name)


    def register_observer(self, observer):
        if observer in self.__observers:
            return # not already registered

        self.__observers.append(observer)
        for key in (self.__properties__.keys() + self.__derived_properties__.keys()):
            self.__add_observer_notification(observer, key)

    def unregister_observer(self, observer):
        if observer not in self.__observers:
            return

        for key in (self.__properties__.keys() + self.__derived_properties__.keys()):
            self.__remove_observer_notification(observer, key)

        self.__observers.remove(observer)

    def _reset_property_notification(self, prop_name):
        """Called when it has be done an assignment that changes the
        type of a property or the instance of the property has been
        changed to a different instance. In this case it must be
        unregistered and registered again"""

        self.register_property(prop_name)

        for observer in self.__observers:
            self.__remove_observer_notification(observer, prop_name)
            self.__add_observer_notification(observer, prop_name)

    def __add_observer_notification(self, observer, prop_name):
        """Searches in the observer for any possible listener, and
        stores the notification methods to be called later"""

        method_name = "property_%s_value_change" % prop_name
        if hasattr(observer, method_name):
            method = getattr(observer, method_name)
            if method not in self.__value_notifications[prop_name]:
                list.append(self.__value_notifications[prop_name], method)

        # is it a signal?
        orig_prop = getattr(self, "_prop_%s" % prop_name)
        if isinstance(orig_prop, Signal):
            method_name = "property_%s_signal_emit" % prop_name
            if hasattr(observer, method_name):
                method = getattr(observer, method_name)
                if method not in self.__signal_notif[prop_name]:
                    list.append(self.__signal_notif[prop_name], method)

        # is it an instance change notification type?
        elif isinstance(orig_prop, ObsWrapperBase):
            method_name = "property_%s_before_change" % prop_name
            if hasattr(observer, method_name):
                method = getattr(observer, method_name)
                if method not in self.__instance_notif_before[prop_name]:
                    list.append(self.__instance_notif_before[prop_name], method)

            method_name = "property_%s_after_change" % prop_name
            if hasattr(observer, method_name):
                method = getattr(observer, method_name)
                if method not in self.__instance_notif_after[prop_name]:
                    list.append(self.__instance_notif_after[prop_name], method)

    def __remove_observer_notification(self, observer, prop_name):
        if self.__value_notifications.has_key(prop_name):
            method_name = "property_%s_value_change" % prop_name
            if hasattr(observer, method_name):
                method = getattr(observer, method_name)
                if method in self.__value_notifications[prop_name]:
                    self.__value_notifications[prop_name].remove(method)

        orig_prop = getattr(self, "_prop_%s" % prop_name)
        # is it a signal?
        if isinstance(orig_prop, Signal):
            method_name = "property_%s_signal_emit" % prop_name
            if hasattr(observer, method_name):
                method = getattr(observer, method_name)
                if method in self.__signal_notif[prop_name]:
                    self.__signal_notif[prop_name].remove(method)

        # is it an instance change notification type?
        elif isinstance(orig_prop, ObsWrapperBase):
            if self.__instance_notif_before.has_key(prop_name):
                method_name = "property_%s_before_change" % prop_name
                if hasattr(observer, method_name):
                    method = getattr(observer, method_name)
                    if method in self.__instance_notif_before[prop_name]:
                        self.__instance_notif_before[prop_name].remove(method)

            if self.__instance_notif_after.has_key(prop_name):
                method_name = "property_%s_after_change" % prop_name
                if hasattr(observer, method_name):
                    method = getattr(observer, method_name)
                    if method in self.__instance_notif_after[prop_name]:
                        self.__instance_notif_after[prop_name].remove(method)

    def __notify_observer__(self, observer, method, *args, **kwargs):
        """This can be overridden by derived class in order to call
        the method in a different manner (for example, in
        multithreading, or a rpc, etc.)  This implementation simply
        calls the given method with the given arguments"""
        return method(*args, **kwargs)


    # ---------- Notifiers:

    def notify_property_value_change(self, prop_name, old, new):
        assert(self.__value_notifications.has_key(prop_name))
        for method in self.__value_notifications[prop_name] :
            obs = method.im_self
            # notification occurs checking spuriousness of the observer
            if old != new or obs.accepts_spurious_change():
                self.__notify_observer__(obs, method,
                                         self, old, new) # notifies the change

    def notify_method_before_change(self, prop_name, instance, meth_name,
                                    args, kwargs):
        assert(self.__instance_notif_before.has_key(prop_name))
        for method in self.__instance_notif_before[prop_name] :
            self.__notify_observer__(method.im_self, method, self, instance,
                                     meth_name, args, kwargs) # notifies the change

    def notify_method_after_change(self, prop_name, instance, meth_name,
                                   res, args, kwargs):
        assert(self.__instance_notif_after.has_key(prop_name))
        for method in self.__instance_notif_after[prop_name] :
            self.__notify_observer__(method.im_self, method, self, instance,
                                     meth_name, res, args, kwargs) # notifies the change

    def notify_signal_emit(self, prop_name, args, kwargs):
        assert(self.__signal_notif.has_key(prop_name))
        for method in self.__signal_notif[prop_name] :
            self.__notify_observer__(method.im_self, method, self,
                                     args, kwargs) # notifies the signal emit



import gtk
# ----------------------------------------------------------------------
class TreeStoreModel (Model, gtk.TreeStore):
    """Use this class as base class for your model derived by
    gtk.TreeStore"""
    __metaclass__  = support.metaclasses.ObservablePropertyGObjectMeta

    def __init__(self, column_type, *args):
        Model.__init__(self)
        gtk.TreeStore.__init__(self, column_type, *args)


# ----------------------------------------------------------------------
class ListStoreModel (Model, gtk.ListStore):
    """Use this class as base class for your model derived by
    gtk.ListStore"""
    __metaclass__  = support.metaclasses.ObservablePropertyGObjectMeta

    def __init__(self, column_type, *args):
        Model.__init__(self)
        gtk.ListStore.__init__(self, column_type, *args)


# ----------------------------------------------------------------------
class TextBufferModel (Model, gtk.TextBuffer):
    """Use this class as base class for your model derived by
    gtk.TextBuffer"""
    __metaclass__  = support.metaclasses.ObservablePropertyGObjectMeta

    def __init__(self, table=None):
        Model.__init__(self)
        gtk.TextBuffer.__init__(self, table)
