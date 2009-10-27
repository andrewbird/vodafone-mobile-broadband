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
Views for the stats window
"""

import os
import gtk
import cairo

from wader.vmc.utils import repr_usage, units_to_bits, bits_to_units, UNIT_MB


class StatsBar(gtk.DrawingArea):

    def __init__(self, label="", value=0, min_value=0,
                    max_value=10, units=UNIT_MB, user_limit=0):
        super(StatsBar, self).__init__()
        self.supports_alpha = False

        #value in bits
        self.value = value
        self.units = units
        #min and max values in self.units
        self.min_value = units_to_bits(min_value, units)
        self.max_value = units_to_bits(max_value, units)
        self.user_limit = units_to_bits(user_limit, units)

        self.connect('expose-event', self.on_expose)
        self.connect('screen-changed', self.on_screen_changed)

    @classmethod
    def init_array(cls, labels, *args, **kwargs):
        """
        This method makes an array of n identical StatsBars
        """
        bars = []
        for label in labels:
            bar = cls(*((label,) + args), **kwargs)
            bars.append(bar)
        return bars

    def on_screen_changed(self, widget, old_screen=None):
        # To check if the display supports alpha channels, get the colormap
        screen = widget.get_screen()
        colormap = screen.get_rgba_colormap()
        if colormap == None:
            colormap = screen.get_rgb_colormap()
            self.supports_alpha = False
        else:
            self.supports_alpha = True

        # Now we have a colormap appropriate for the screen, use it
        widget.set_colormap(colormap)

        return False

    def on_expose(self, widget, event):
        if not widget.window:
            return
        cr = widget.window.cairo_create()

        if self.supports_alpha:
        #if 0:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.0) # Transparent
        else:
            cr.set_source_rgb(1.0, 1.0, 1.0) # Opaque white

        # Draw the background
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

        x, y, width, height = widget.get_allocation()
        cr.set_source_rgba(.8, 0.8, 0.8, 0.4)

        cr.rectangle(1.0, 1.0, width - 1.0, height - 1.0)
        # Draw a rectangle (and fill background)
        cr.fill()
        #cr.stroke()

        inner_width = width * .75
        self.draw_limits(cr, inner_width, height)
        self.draw_usage(cr, inner_width, height)
        # Draw inner rectangle
        cr.set_line_width(.8)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.rectangle(0, 0, inner_width, height)
        cr.stroke()
        # Draw outer rectangle
        cr.set_line_width(1.0)
        cr.rectangle(0, 0, width, height)
        cr.stroke()

        return False

    def draw_limits(self, cr, inner_width, height):
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.set_line_width(.1)
        step = float(height) / bits_to_units(self.max_value, self.units)
        frange = lambda a, b, step : [
                                x * step for x in xrange(a,int(b*(1/step)))]
        for i in frange(0, height + step, step):
            cr.move_to(inner_width - 5, height - i)
            cr.line_to(inner_width - 15, height - i)
            cr.stroke()

        # Draw limits
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.select_font_face("Verdana",
                            cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)

        #font_size = height * .022
        #cr.set_font_size(font_size)

        # upper limit
        cr.move_to(inner_width + 4, height * .03)
        cr.show_text(repr_usage(self.max_value, self.units))
        # upper mid limit
        cr.move_to(inner_width + 4, height * .25)
        cr.show_text(repr_usage(self.max_value * .75, self.units))
        # mid limit
        cr.move_to(inner_width + 4, height * .5)
        cr.show_text(repr_usage(self.max_value * .5, self.units))
        # down mid limit
        cr.move_to(inner_width + 4, height * .75)
        cr.show_text(repr_usage(self.max_value * .25, self.units))
        # down limit (0)
        cr.move_to(inner_width + 4, height * .99)
        cr.show_text(repr_usage(0, self.units))

    def draw_usage(self, cr, inner_width, height):
        threshold = self._fraction()
        usage_height = height - (threshold * height)
        #linear = cairo.LinearGradient(0.85, 0.85, 0.85, 0.65)
        #linear.add_color_stop_rgba(.9, 0.9, 0.9, 0.9, 0.5)
        cr.set_source_rgba(0.7, 0.7, 0.7, 0.9)
        cr.rectangle(5, usage_height, inner_width-10, height)
        cr.fill()

        if self.user_limit and self.value > self.user_limit:
            limit = self._fraction(self.value - self.user_limit)
            limit = limit * height
            cr.set_source_rgba(5.0, 0, 0, 0.5)
            cr.rectangle(5, usage_height, inner_width-10, limit)
            cr.fill()

    def _fraction(self, value=None):
        if not value:
            value = self.value
        value = float(value - self.min_value)
        max_value = self.max_value - self.min_value
        return value / max_value

    def update(self):
        assert self.max_value > self.value
        self.emit('expose-event', gtk.gdk.Event(gtk.gdk.EXPOSE))
        self.queue_draw()

    def set_value(self, value):
        if value == self.value: return
        if value >= self.max_value:
            self.max_value = 1.25 * value
        self.value = value
        self.update()

    def set_max_value(self, max_value):
        if max_value == self.max_value: return
        self.max_value = max_value
        if self.value >= self.max_value:
            self.max_value = 1.25 * self.value
        self.update()

    def set_user_limit(self, user_limit):
        if user_limit == self.user_limit: return
        self.user_limit = user_limit
        self.update()


