#  Author: Roberto Cavada <cavada@fbk.eu>
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
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor,
#  Boston, MA 02110, USA.
#
#  For more information on pygtkmvc see <http://pygtkmvc.sourceforge.net>
#  or email to the author Roberto Cavada <cavada@fbk.eu>.
#  Please report bugs to <cavada@fbk.eu>.

from metaclass_base import PropertyMeta
import types


class ObservablePropertyMeta (PropertyMeta):
    """Classes instantiated by this meta-class must provide a method named
    notify_property_change(self, prop_name, old, new)"""
    def __init__(cls, name, bases, dict):
        PropertyMeta.__init__(cls, name, bases, dict)
        return    
    
    def get_setter_source(cls, setter_name, prop_name):
        return """def %(setter)s(self, val): 
 old = self._prop_%(prop)s
 new = type(self).create_value('%(prop)s', val, self)
 self._prop_%(prop)s = new
 if type(self).check_value_change(old, new): self._reset_property_notification('%(prop)s')
 self.notify_property_value_change('%(prop)s', old, val)
 return
""" % {'setter':setter_name, 'prop':prop_name}

    pass #end of class


class ObservablePropertyMetaMT (ObservablePropertyMeta):
    """This class provides multithreading support for accesing
    properties, through a locking mechanism. It is assumed a lock is
    owned by the class that uses it. A Lock object called _prop_lock
    is assumed to be a member of the using class. see for example class
    ModelMT"""
    def __init__(cls, name, bases, dict):
        ObservablePropertyMeta.__init__(cls, name, bases, dict)
        return 
    
    def get_setter_source(cls, setter_name, prop_name):
        return """def %(setter)s(self, val): 
 old = self._prop_%(prop)s
 new = type(self).create_value('%(prop)s', val, self)
 self._prop_lock.acquire()
 self._prop_%(prop)s = new
 self._prop_lock.release()
 if type(self).check_value_change(old, new): self._reset_property_notification('%(prop)s')
 self.notify_property_value_change('%(prop)s', old, val)
 return
""" % {'setter':setter_name, 'prop':prop_name}

    pass #end of class


try:
    from gobject import GObjectMeta
    class ObservablePropertyGObjectMeta (ObservablePropertyMeta, GObjectMeta): pass
    class ObservablePropertyGObjectMetaMT (ObservablePropertyMetaMT, GObjectMeta): pass    
except:
    class ObservablePropertyGObjectMeta (ObservablePropertyMeta): pass
    class ObservablePropertyGObjectMetaMT (ObservablePropertyMetaMT): pass
    pass


