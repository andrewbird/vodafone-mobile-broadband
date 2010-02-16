#  Author: Roberto Cavada <cavada@fbk.eu>
#
#  Copyright (c) 2007 by Roberto Cavada
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


import types
import gtk
import time

#from gtkmvc.adapters.default import * 
from default import * 
#from gtkmvc.observer import Observer
from wader.vmc.contrib.gtkmvc.observer import Observer


# ----------------------------------------------------------------------
class Adapter (Observer):

    def __init__(self, model, prop_name,
                 prop_read=None, prop_write=None, 
                 value_error=None):
        """
        Creates a new adapter that handles setting of value of a
        model single model property when a corresponding widgets set
        is changed and viceversa when the property is also
        observable.

        This class handles only assignments to properties. For other
        kinds of setting (e.g. user-defined classes used as
        observable properties, containers, etc.) use other types of
        Adapters derived from this class.
        
        prop_name is the model's property name (as a string). It is
        possible to use a dotted notation to identify a property
        contained into a hierarchy of models. For example 'a.b.c'
        identifies property 'c' into model 'b' inside model 'a',
        where model 'a' is an attribute of given top level model.
        Last name must be an observable or non-observable attribute,
        and previous names (if specified) must all refer to
        instances of class Model. First name from the left must be
        the name of a model instance inside the given model.

        prop_{write,read} are two optional functions that apply
        custom modifications to the value of the property before
        setting and reading it. Both take a value and must return a
        transformed value whose type must be compatible with the
        type of the property.
        
        value_error can be a function (or a method) to be called
        when a ValueError exception occurs while trying to set a
        wrong value for the property inside the model. The function
        will receive: the adapter, the property name and the value
        coming from the widget that offended the model.
        """

        # registration is delayed, as we need to create possible
        # listener before:
        Observer.__init__(self)        

        self._prop_name = prop_name
        self._prop_read = prop_read
        self._prop_write = prop_write
        self._value_error = value_error
        self._wid = None
        self._wid_info = {}
        
        # this flag is set when self is changing the property or the
        # widget, in order to avoid infinite looping.
        self._itsme = False 

        self._connect_model(model)
        return

    def connect_widget(self, wid,
                       getter=None, setter=None, 
                       signal=None, arg=None, update=True):

        """
        Called when the widget is instantiated, and the adapter is
        ready to connect the widget and the property inside the
        observed model. arg is the (optional) argument that will be
        passed when connecting the signal.

        getter and setter are the (optional) methods used
        for reading and writing the widget's value. When not
        specified, default getter and setter will be guessed by
        looking at the widget type the adapter will be connected
        with. Guessing is carried out by querying information
        specified into module 'adapters.default'. 

        Finally, if update is false, the widget will not be updated
        """

        if self._wid_info.has_key(wid):
            raise ValueError("Widget " + str(wid) + " was already connected")
        
        wid_type = None

        if None in (getter, setter, signal):
            w = search_adapter_info(wid)
            if getter is None: getter = w[GETTER]
            if setter is None:
                setter = w[SETTER]
                wid_type = w[WIDTYPE]
                pass
            
            if signal is None: signal = w[SIGNAL]
            pass

        # saves information about the widget
        self._wid_info[wid] = (getter, setter, wid_type)

        # connects the widget
        if signal:
            if arg: wid.connect(signal, self._on_wid_changed, arg)
            else: wid.connect(signal, self._on_wid_changed)
            pass

        self._wid = wid

        # updates the widget:
        if update: self.update_widget()
        return
        
    def update_model(self):
        """Forces the property to be updated from the value hold by
        the widget. This method should be called directly by the
        user in very unusual conditions."""
        self._write_property(self._read_widget())
        return
    
    def update_widget(self):
        """Forces the widget to be updated from the property
        value. This method should be called directly by the user
        when the property is not observable, or in very unusual
        conditions."""
        self._write_widget(self._read_property())
        return


    # ----------------------------------------------------------------------
    #  Private methods
    # ----------------------------------------------------------------------
    def _connect_model(self, model):
        """
        Used internally to connect the property into the model, and
        register self as a value observer for that property"""

        parts = self._prop_name.split(".")
        if len(parts) > 1:
            # identifies the model
            models = parts[:-1]
            for name in models:
                model = getattr(model, name)
                if not isinstance(model, gtkmvc.Model):
                    raise TypeError("Attribute '" + name +
                                    "' was expected to be a Model, but found: " +
                                    str(model))
                pass
            prop = parts[-1]
        else: prop = parts[0]

        # prop is inside model?
        if not hasattr(model, prop):
            raise ValueError("Attribute '" + prop +
                             "' not found in model " + str(model))

        # is it observable?
        if model.has_property(prop):
            # we need to create an observing method before registering
            self._add_method(self._get_observer_src(prop))
            pass

        self._prop = getattr(model, prop)
        self._prop_name = prop
        
        # registration of model:
        self.register_model(model)
        return
    

    def _get_observer_src(self, prop_name):
        """This is the code for an value change observer"""
        return """def property_%s_value_change(self, model, old, new):
 if self._itsme or old == new: return
 self._on_prop_changed()""" % prop_name


    def _add_method(self, src):
        """Private service to add a new method to the instance,
        given method code"""
        
        from gtkmvc.support.utils import get_function_from_source
        import new
        
        func = get_function_from_source(src)
        meth = new.instancemethod(func, self, self.__class__)
        setattr(self, func.__name__, meth)
        return

    def _get_property(self):
        """Private method that returns the value currently stored
        into the property"""
        return getattr(self.get_model(), self._prop_name)
        #return self._prop # bug fix reported by A. Dentella

    def _set_property(self, val):
        """Private method that sets the value currently of the property."""
        return setattr(self.get_model(), self._prop_name, val)

    def _read_property(self, *args):
        """Returns the (possibly transformed) value that is stored
        into the property"""
        if self._prop_read: return self._prop_read(self._get_property(*args))
        return self._get_property(*args)

    def _write_property(self, val, *args):
        """Sets the value of property. Given val is transformed
        accodingly to prop_write function when specified at
        construction-time. A try to cast the value to the property
        type is given."""

        # 'finally' would be better here, but not supported in 2.4 :(
        try: 
            totype = type(self._get_property(*args))
            val_prop = self._cast_value(val, totype)
            if self._prop_write: val_prop = self._prop_write(val_prop)

            self._itsme = True
            self._set_property(val_prop, *args)

        except ValueError:
            self._itsme = False
            if self._value_error: self._value_error(self, self._prop_name, val)
            else: raise
            pass

        except: self._itsme = False; raise

        self._itsme = False
        return

    def _read_widget(self):
        """Returns the value currently stored into the widget, after
        transforming it accordingly to possibly specified function."""
        getter = self._wid_info[self._wid][0]
        return getter(self._wid)
        
    def _write_widget(self, val):
        """Writes value into the widget. If specified, user setter
        is invoked."""
        self._itsme = True
        try:
            setter = self._wid_info[self._wid][1]
            wtype = self._wid_info[self._wid][2]
            if wtype is not None: setter(self._wid, self._cast_value(val, wtype))
            else: setter(self._wid, val)            
        finally:
            self._itsme = False
            pass
        
        return
         
    def _cast_value(self, val, totype):
        """Casts given val to given totype. Raises TypeError if not able to cast."""
        t = type(val)
        if issubclass(t, totype): return val
        if issubclass(totype, types.StringType): return str(val)
        if issubclass(t, types.StringType): 
            if issubclass(totype, types.IntType):
                if val: return int(float(val))
                return 0
            if issubclass(totype, types.FloatType):
                if val: return float(val)
                return 0.0
            pass
        
        raise TypeError("Not able to cast " + str(t) + " to " + str(totype))


    # ----------------------------------------------------------------------
    # Callbacks and observation
    # ----------------------------------------------------------------------

    def _on_wid_changed(self, wid):
        """Called when the widget is changed"""
        if self._itsme: return
        self.update_model()
        return

    def _on_prop_changed(self):
        """Called by the observation code, when the value in the
        observed property is changed"""
        if not self._itsme: self.update_widget()
        return

    pass # end of class Adapter



#----------------------------------------------------------------------
class UserClassAdapter (Adapter):
    """
    This class handles the communication between a widget and a
    class instance (possibly observable) that is a property inside
    the model. The value to be shown is taken and stored by using a
    getter and a setter. getter and setter can be: names of user
    class methods, bound or unbound methods of the user class, or a
    function that will receive the user class instance and possible
    arguments whose number depends on whether it is a getter or a
    setter."""
    
    def __init__(self, model, prop_name,
                 getter, setter, 
                 prop_read=None, prop_write=None,                   
                 value_error=None):

        Adapter.__init__(self, model, prop_name,
                         prop_read, prop_write, value_error)

        self._getter = self._resolve_to_func(getter)
        self._setter = self._resolve_to_func(setter)
        return

    # ----------------------------------------------------------------------
    # Private methods 
    # ----------------------------------------------------------------------

    def _resolve_to_func(self, what):
        """This method resolves whatever is passed: a string, a
        bound or unbound method, a function, to make it a
        function. This makes internal handling of setter and getter
        uniform and easier."""
        if isinstance(what, types.StringType):
            what = getattr(Adapter._get_property(self), what)
            pass

        # makes it an unbounded function if needed
        if type(what) == types.MethodType: what = what.im_func

        if not type(what) == types.FunctionType: raise TypeError("Expected a method name, a method or a function")
        return what
    

    def _get_observer_src(self, prop_name):
        """This is the code for a method after_change observer"""
        return """def property_%s_after_change(self, model, \
   instance, meth_name, res, args, kwargs):
 if self._itsme: return
 self._on_prop_changed(instance, meth_name, res, args, kwargs)""" % prop_name

    
    def _on_prop_changed(self, instance, meth_name, res, args, kwargs):
        """Called by the observation code, when a modifying method
        is called"""
        Adapter._on_prop_changed(self)
        return

    def _get_property(self, *args):
        """Private method that returns the value currently stored
        into the property"""
        val = self._getter(Adapter._get_property(self), *args)
        if self._prop_read: return self._prop_read(val, *args)
        return val

    def _set_property(self, val, *args):
        """Private method that sets the value currently of the property"""
        if self._prop_write: val = self._prop_write(val)
        return self._setter(Adapter._get_property(self), val, *args)
    
    pass # end of class UserClassAdapter
# ----------------------------------------------------------------------



#----------------------------------------------------------------------
class RoUserClassAdapter (UserClassAdapter):
    """
    This class is for Read-Only user classes. RO classes are those
    whose setting methods do not change the instance, but return a
    new instance that has been changed accordingly to the setters
    semantics. An example is python datetime class, whose replace
    method does not change the instance it is invoked on, but
    returns a new datetime instance.

    This class is likely to be used very rarely. 
    """
    
    def __init__(self, model, prop_name,
                 getter, setter, 
                 prop_read=None, prop_write=None,                   
                 value_error=None):

        UserClassAdapter.__init__(self, model, prop_name,
                                  getter, setter,
                                  prop_read, prop_write, value_error)

        return

    # ----------------------------------------------------------------------
    # Private methods 
    # ----------------------------------------------------------------------

    def _set_property(self, val, *args):
        """Private method that sets the value currently of the property"""
        val = UserClassAdapter._set_property(self, val, *args)
        if val: Adapter._set_property(self, val, *args)
        return val
    
    pass # end of class RoUserClassAdapter
# ----------------------------------------------------------------------
