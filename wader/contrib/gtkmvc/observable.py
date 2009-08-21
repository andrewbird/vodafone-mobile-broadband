#  -------------------------------------------------------------------------
#  Author: Roberto Cavada <cavada@irst.itc.it>
#
#  Copyright (C) 2006 by Roberto Cavada
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
#  51 Franklin Street, Fifth Floor,
#  Boston, MA 02110, USA.ridge, MA 02139, USA.
#
#  For more information on pygtkmvc see <http://pygtkmvc.sourceforge.net>
#  or email to the author <cavada@irst.itc.it>.
#  -------------------------------------------------------------------------


from support import decorators
from support.wrappers import ObsWrapperBase

# ----------------------------------------------------------------------
class Observable (ObsWrapperBase):
    def __init__(self):
        ObsWrapperBase.__init__(self)
        return
    pass # end of class


@decorators.good_decorator
def observed(func):
    """Use this decorator to make your class methods observable.

    Your observer will receive at most two notifications:
      - property_<name>_before_change
      - property_<name>_after_change

    """

    def wrapper(*args, **kwargs):
        self = args[0]
        assert(isinstance(self, Observable))

        self._notify_method_before(self, func.__name__, args, kwargs)
        res = func(*args, **kwargs)
        self._notify_method_after(self, func.__name__, res, args, kwargs)
        return res
    return wrapper


# ----------------------------------------------------------------------
class Signal (Observable):
    """Base class for signals properties"""
    def __init__(self):
        Observable.__init__(self)

    def emit(self, *args, **kwargs):
        return self.__get_model__().notify_signal_emit(
            self.__get_prop_name__(), args, kwargs)

