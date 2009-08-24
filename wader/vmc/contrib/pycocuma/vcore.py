# -*- coding: utf-8 -*-
"""
 vCard 3.0 and iCalendar 2.0 Core Types and Functions as described in RFC 2425
 (A MIME Content-Type for Directory Information)
"""
# Copyright (C) 2004  Henning Jacobs <henning@srcco.de>
# Copyright (C) 2009  Vodafone España, S.A.
#                     Andrew Bird
#                         Updated for Python 2.6
#                         Cut down to just the vcf parsing
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  $Id: vcore.py 82 2004-07-11 13:01:44Z henning $

import re
from types import *

VALUE_DELIM_RE  = re.compile(r"(?<!\\);")
PARAM_RE        = re.compile(r'([-a-zA-Z]*)=?("[^"]*"|[^:]*)')
CONTENT_LINE_RE = re.compile(r"[ \t]*" # Leading Whitespace
                             r"([a-zA-Z0-9\-]+\.|)" #GROUP
                             r"([a-zA-Z0-9\-]+)" #NAME
                             r"(;.*|)" #PARAM
                             r":(.*)" #VALUE
                             r"[ \t\n\r]*") # Trailing Whitespace

# NOTE: vcf is the file extension for vCards
# and ics is the ext. for vCalendar (iCalendar)
# VCF means VCard/Calendar Format here

def getvcfrepr(obj):
    "Helper Function"
    return obj.VCF_repr()

def getsubattr(obj, attrpath):
    attrs = attrpath.split(".")
    ret = obj
    for attr in attrs:
        if type(ret) == ListType:
            ret = [getattr(listitem, attr, None) for listitem in ret]
        else:
            ret = getattr(ret, attr, None)
            if type(ret) == MethodType:
                ret = vC_value(ret())
    return ret

def flattenattr(attr):
    """Returns string: 'value (param1, param2, ..)'
    attr is vC_value"""
    ret = attr.get()
    try:
        paramstr = "("+ ", ".join(attr.params.get("type")) +")"
        ret = ret + " " + paramstr
    except:
        pass
    return ret

def deescape(text):
    "Deescape special vCard/vCalendar chars"
    return text.replace(r"\\", "\\").replace(r"\n", "\n").replace(r"\N", "\n").\
                            replace(r"\;", ";").replace(r"\,", ",")

def escape(text):
    "Escape special chars"
    return text.replace("\\", r"\\").replace("\n", r"\n").replace(";", r"\;").replace(",", r"\,")

def escapexml(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def quoteParamValue(str):
    # Has to be quoted?
    # Check for non-safe chars:
    if str.find('=') != -1 \
      or str.find(';') != -1\
      or str.find(':') != -1\
      or str.find(',') != -1:
        return "\""+str+"\""
    else:
        return str

def chop_line(line):
    "Truncate line breaks"
    while len(line) and line[-1] in ["\r","\n"]:
        line=line[:-1]
    return line

def isNonEmptyLine(line):
    """are there characters other than space?

    used especially with filter()
    """
    line = chop_line(line)
    if line:
        ret = not line.isspace()
    else:
        ret = False
    return ret

def makeloglines(physical_lines):
    "Line De-Folding (RFC 2425): turn physical lines into logical ones"
    i = 0
    while i < len(physical_lines):
        if i > 0 and len(physical_lines[i]) >= 2:
            # Line is continued if next phy. line starts with
            # single space or tab:
            if physical_lines[i][0] in " \t":
                physical_lines[i-1] =\
                chop_line(physical_lines[i-1]) + physical_lines[i][1:]
                del physical_lines[i]
            else:
                i += 1
        else:
            i += 1

def log2phylines(logical_line):
    "Fold(break) Lines longer than 75-Chars"
    # Max-Length of physical Line:
    i = 75
    result = logical_line
    while True:
        if i < len(logical_line):
            # Break with CR and start next line with single space character:
            result = result[:i] + "\n " + result[i:]
        else:
            break
        i += 76
    return result

def getitem(seq, idx, default=None):
    "Return List Item or default if idx is out of range"
    if len(seq) > idx:
        return seq[idx]
    else:
        return default

def gettuple(seq, length, default=None):
    "Fills seq up to length with default and return tuple"
    if len(seq) < length:
        if callable(default):
            ret = seq
            for i in range(length - len(seq)):
                    ret.append(default())
            return tuple(ret)
        else:
            return tuple(seq) + tuple(((length - len(seq))*[default]))
    else:
        return tuple(seq)


class vC_params:
    "Parameters used by all vCard/vCalendar records"
    def __init__(self, text=""):
        self.dict = {}
        self.parse(text)

    def parse(self, text):
        params = VALUE_DELIM_RE.split(text)
        for param in params:
            matchobj = PARAM_RE.match(param)
            if matchobj:
                param_name = matchobj.group(1).lower()
                param_value = matchobj.group(2)
                if param_value != "":
                    # Compat: Version 2 of vCard had no TYPE param:
                    if param_name == "": param_name = "type"
                    # Is the Value a quoted String? (DQUOTE str DQUOTE)
                    if param_value[0] == "\"" and param_value[-1] == "\"" \
                       and len(param_value) > 1:
                        param_value = param_value[1:-1] # DeQuote

                    #self.dict.setdefault(param_name, self.Set()).extend(param_value.split(","))
                    self.dict.setdefault(param_name, set(param_value.split(",")))

    def get(self, param_name):
        return self.dict.get(param_name, None)

    def set(self, param_name, param_value):
        self.dict[param_name] = param_value

    def VCF_repr(self):
        ret = ""
        for key, value in zip(self.dict.keys(), self.dict.values()):
            ret = ret + ";" + key.upper() + "=" + ",".join(map(quoteParamValue,value.items()))
        return ret

    def XML_repr(self):
        if not self.dict:
            return ''
        ret = ""
        # XXX: This is only for vCard-RDF!
        for item in self.dict.get('type', []):
            ret = ret + '<rdf:type rdf:resource="http://www.w3.org/2001/vcard-rdf/3.0#' + escapexml(item) + '"/>'
        return ret

    def __repr__(self):
        return "<%s: %s>" % (self.__class__, repr(self.dict))


class vC_contentline:
    "Logical vCard/vCalendar Content Line"
    def __init__(self, text):
        self.name = ""
        self.params = ""
        self.value = ""
        self.parse(text)

    def parse(self, text):
        matchobj = CONTENT_LINE_RE.match(chop_line(text))
        if matchobj:
            self.group = matchobj.group(1)[:-1].upper()
            self.name = matchobj.group(2).upper()
            self.params = vC_params(matchobj.group(3))
            self.value = matchobj.group(4)
        else:
            #XXX: maybe we need to be a little more clever with stdout, but it should
            #     end up in twisted's log
            print "WARNING: Illegal vCard/vCalendar contentline: '%s'" % text

    def VCF_repr(self):
        ret = ""
        if self.group:
                ret = ret + self.group + "."
        ret = ret + self.name + str(self.params) + ":" + self.value
        return ret


class vC_AbstractBaseValue:
    "Abstract Base Class for all vCard/vCalendar leaf nodes"
    def VCF_repr(self):
        "Return VCF representation of value"
        raise NotImplementedError

    def XML_repr(self):
        raise NotImplementedError

    def get(self):
        "Return value as String"
        raise NotImplementedError

    def set(self, value):
        "Set value (value should be a string)"
        raise NotImplementedError

    def is_empty(self):
        "Test value for emptieness"
        raise NotImplementedError


class vC_AbstractCompoundValue:
    "Abstract Base Class for all vCard compound values (n, adr, org)"
    def __repr__(self):
        return "<%s: %s>" % (self.__class__, repr(self.__dict__))

    def is_empty(self):
        "return True if value is empty"
        raise NotImplementedError

    def VCF_repr(self):
        "Return VCF representation of value"
        raise NotImplementedError

    def XML_repr(self):
        raise NotImplementedError


class vC_value(vC_AbstractBaseValue):
    "Raw Value used by vC_text"
    def __init__(self, value=""):
        self.__data = deescape(value)

    def VCF_repr(self):
        return escape(self.__data)

    def XML_repr(self):
        return escapexml(self.__data)

    def set(self, value):
        self.__data = value

    def get(self):
        return self.__data

    def is_empty(self):
        return self.__data == ""

    def __repr__(self):
        return "<%s: %s>" % (self.__class__, repr(self.__data))


class vC_text(vC_AbstractBaseValue):
    "vCard/vCalendar Text Value (encapsulates vC_value and vC_params)"
    def __init__(self, value="", params=None):
        if params is None:
            params = vC_params()
        self.params = params
        self.value = vC_value(value)

    def get(self):
        return self.value.get()

    def set(self, val):
        self.value.set(val)

    def is_empty(self):
        return self.value.is_empty()

    def VCF_repr(self):
        return self.params.VCF_repr() + ":" + self.value.VCF_repr()

    def XML_repr(self):
        paramxml = self.params.XML_repr()
        if paramxml:
            return "<rdf:value>"+self.value.XML_repr()+"</rdf:value>" + paramxml
        else:
            return self.value.XML_repr()

    def __repr__(self):
        return "<%s: %s %s>" % (self.__class__, repr(self.value), repr(self.params))


class vC_categories(vC_text):
    def VCF_repr(self):
        # value includes ',' therefore do not escape in a whole:
        ret = self.params.VCF_repr() + ":" + ','.join(\
            map(escape, self.value.get().split(',')))
        return ret


class vC_geo(vC_text):
    def VCF_repr(self):
        # value includes ';' therefore do not escape:
        ret = self.params.VCF_repr() + ":" + self.value.get()
        return ret


class vC_datetime(vC_AbstractBaseValue):
    "vCard/vCalendar DateTime Value Type"
    # TODO: Datetime is UTC, support TimeZones!
    def __init__(self, value=None, params=vC_params()):
        self.params = params
        self.dateonly = False
        self.value = None
        self.set(value)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__, self.get())

    def is_empty(self):
        return self.value is None

    def getDate(self):
        "get date as string (YYYY-MM-DD)"
        if self.value is not None:
            return "%04d-%02d-%02d" % self.value[0:3]
        else:
            return ""

    def getTime(self):
        "get time as string (HH:MM:SS)"
        if self.value is not None and not self.dateonly:
            return "%02d:%02d:%02d" % self.value[3:6]
        else:
            return ""

    def setDate(self, d):
        "set date from given string (YYYY-MM-DD)"
        if self.value is None:
            self.value = (0,0,0,0,0,0,0,0,0)
        try:
            if d.find("-") != -1:
                d = gettuple(map(int, d.split("-")), 3, 0)
            else:
                d = tuple(map(int, (d[0:4], d[4:6], d[6:8])))
            self.value = d + self.value[3:]
        except ValueError:
            # Date-String was probably incorrect: We clear ourself:
            self.value = None

    def setTime(self, t):
        "set time from given string (HH:MM:SS)"
        if self.value is None:
            self.value = (0,0,0,0,0,0,0,0,0)
            #XXX: maybe we need to be a little more clever with stdout, but it should
            #     end up in twisted's log
            print 'vC_datetime.setTime(): Setting Time, but Date not set!'
        try:
            if t.find(":") != -1:
                if t[-1:] == "Z": t = t[:-1]
                t = gettuple(map(int, t.split(":")), 3, 0)
            else:
                t = tuple(map(int, (t[0:2], t[2:4], t[4:6])))
            self.value = self.value[0:3] + t + self.value[6:]
            self.dateonly = False
        except ValueError:
            # Something has gone wrong: Set Time to Zero:
            self.value = self.value[0:3] + (0,0,0) + self.value[6:]
            self.dateonly = True

    def get(self):
        if self.value is not None:
            if self.dateonly:
                ret = self.getDate()
            else:
                ret = self.getDate() + ' ' + self.getTime()
        else:
            ret = ""
        return ret

    def set(self, value):
        if (type(value) is StringType or\
          type(value) is UnicodeType):
            # Unpack datetime string (YYYY-MM-DDTHH:MM:SS[Z]):
            d, t = gettuple(value.split('T'), 2)
            if not t:
                # try wspace-char as date-time separator:
                d, t = gettuple(value.split(' '), 2)
            self.setDate(d)
            if t:
                self.setTime(t)
            else:
                self.dateonly = True
        elif value:
            # value is (hopefully) a time.struct_time tuple:
            self.value = value
        else:
            self.value = None

    def VCF_repr(self):
        if self.value is not None:
            # To comply with RFC 2445 (iCalendar)
            # DateTime does not include "-" nor ":":
            if self.dateonly:
                datetimestr = "%04d%02d%02d" % self.value[0:3]
            else:
                datetimestr = "%04d%02d%02dT%02d%02d%02dZ" % self.value[0:6]
        else:
            datetimestr = ""
        return self.params.VCF_repr() + ":" + datetimestr

    def XML_repr(self):
        if self.value is not None:
            if self.dateonly:
                datetimestr = "%04d%02d%02d" % self.value[0:3]
            else:
                datetimestr = "%04d%02d%02dT%02d%02d%02dZ" % self.value[0:6]
        else:
            datetimestr = ""
        return datetimestr


