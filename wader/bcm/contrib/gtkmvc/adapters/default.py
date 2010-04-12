__all__ = ("search_adapter_info",
           "SIGNAL", "GETTER", "SETTER", "WIDTYPE")

import types
import gtk

# ----------------------------------------------------------------------
# This list defines a default behavior for widgets.
# If no particular behaviour has been specified, adapters will
# use information contained into this list to create themself.
# This list is ordered: the earlier a widget occurs, the better it
# will be matched by the search function. 
# ----------------------------------------------------------------------
__def_adapter = [ # class, default signal, getter, setter, value type
    (gtk.Entry, "changed", gtk.Entry.get_text, gtk.Entry.set_text, types.StringType),
    (gtk.Label, None, gtk.Label.get_text, gtk.Label.set_text, types.StringType),
    (gtk.Arrow, None, lambda a: a.get_property("arrow-type"),
     lambda a,v: a.set(v,a.get_property("shadow-type")), gtk.ArrowType),
    (gtk.ToggleButton, "toggled", gtk.ToggleButton.get_active, gtk.ToggleButton.set_active, types.BooleanType),
    (gtk.CheckMenuItem, "toggled", gtk.CheckMenuItem.get_active, gtk.CheckMenuItem.set_active, types.BooleanType),
    (gtk.Expander, "activate", lambda w: not w.get_expanded(), gtk.Expander.set_expanded, types.BooleanType),
    (gtk.ColorButton, "color-set", gtk.ColorButton.get_color, gtk.ColorButton.set_color, gtk.gdk.Color),
    (gtk.ColorSelection, "color-changed", gtk.ColorSelection.get_current_color, gtk.ColorSelection.set_current_color, gtk.gdk.Color),    
    ]

if gtk.pygtk_version >= (2,10,0):
    # conditionally added support
    __def_adapter.append(
        (gtk.LinkButton, "clicked", gtk.LinkButton.get_uri, gtk.LinkButton.set_uri, types.StringType))
    pass


# constants to access values:
SIGNAL  =1
GETTER  =2
SETTER  =3
WIDTYPE =4
# ----------------------------------------------------------------------


# To optimize the search
__memoize__ = {}    
def search_adapter_info(wid):
    """Given a widget returns the default tuple found in __def_adapter""" 
    t = type(wid)
    if __memoize__.has_key(t): return __memoize__[t]

    for w in __def_adapter:
        if isinstance(wid, w[0]):
            __memoize__[t] = w
            return w
        pass

    raise TypeError("Adapter type " + str(t) + " not found among supported adapters")
        
