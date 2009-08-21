# -*- coding: utf-8 -*-
"""
 vCard 3.0 Implementation as described in RFC 2426
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
#  $Id: vcard.py 94 2004-12-06 21:10:31Z henning $

import re, time
from types import *
import string
from vmc.contrib.pycocuma.vcore import *

FIELDNAMES = [
    "FormattedName",
    "DisplayName", # virtual (does not map to a real vCard field)
    "Family",
    "Given",
    "Additional",
    "Prefixes",
    "Suffixes",
    "NickName",
    "Birthday",
    "Organization",
    "Units",
    "Title",
    "Role",
    "Phone",
    "Email",
    "Mailer",
    "POBox",
    "Extended",
    "Street",
    "PostalCode",
    "City",
    "Region",
    "Country",
    "Label",
    "Note",
    "Categories",
    "SortName", # virtual
    "SortString",
    "URL",
    "Key",
    "TimeZone",
    "GlobalPosition",
    "Photo",
    "Logo",
    "Rev",
    "UID"]

ADRFIELDS = ["POBox", "Extended", "Street", "PostalCode", "City", "Region", "Country"]

FIELDNAME2ATTR = {"FormattedName":"fn", "DisplayName":"getDisplayName", "Family":"n.family", "Given":"n.given", "Additional":"n.additional",
    "Prefixes":"n.prefixes", "Suffixes":"n.suffixes", "NickName":"nickname",
    "Birthday":"bday", "Organization":"org.org", "Units":"org.units", "Title":"title",
    "Role":"role", "Phone":"tel", "Email":"email", "Mailer":"mailer",
    "POBox":"adr.pobox", "Extended":"adr.extended", "Street":"adr.street", "City":"adr.city",
    "Region":"adr.region", "PostalCode":"adr.postcode", "Country":"adr.country",
    "Label":"label",
    "Note":"note", "Categories":"categories", "SortName":"getSortName", "SortString":"sort_string", "URL":"url", "Key":"key",
    "TimeZone":"tz", "GlobalPosition":"geo", "Photo":"photo", "Logo":"logo",
    "Rev":"rev", "UID":"uid" 
    }

vC_adr_types = ["pref", "home", "work", "intl", "postal", "parcel", 
    "dom"] # DOMestic is currently not supported in PyCoCuMa
vC_adr_types_default = ["intl", "postal", "parcel", "work"]

vC_tel_types = ["pref", "home", "work", "voice", "cell", "pager",
    "car", "fax", "modem", "msg", "isdn", "video",
    "bbs", "pcs"] # BBS and PCS are currently not supported in PyCoCuMa
vC_tel_types_default = ["voice"]

vC_email_types = ["pref",
    "internet", "x400"] # These will not display in PyCoCuMa 
vC_email_types_default = ["internet"]

SUPPORTED_VERSIONS = ["2.1", "3.0"]

class vC_n(vC_AbstractCompoundValue):
    "vCard Name record"
    def __init__(self, value="", params=None):
        if params is None:
            params = vC_params()
        self.params = params
        parts = VALUE_DELIM_RE.split(value)
        self.family,\
        self.given,\
        self.additional,\
        self.prefixes,\
        self.suffixes = gettuple(map(vC_value, parts), 5, vC_value)

    def is_empty(self):
        return False

    def getFamilyGiven(self):
        fam = self.family.get()
        giv = self.given.get()
        if fam and giv:
            return fam + ", " + giv
        else:
            return fam or giv or ""

    def VCF_repr(self):
        ret = self.params.VCF_repr() + ":"
        ret = ret +  ";".join(map(getvcfrepr, [self.family,\
                self.given,\
                self.additional,\
                self.prefixes,\
                self.suffixes]))
        return ret

    def XML_repr(self):
        ret = "<vCard:Family>%s</vCard:Family><vCard:Given>%s</vCard:Given><vCard:Other>%s</vCard:Other><vCard:Prefix>%s</vCard:Prefix>"
        ret = ret + "<vCard:Suffix>%s</vCard:Suffix>"
        ret = ret % tuple(map(lambda x: x.XML_repr(), [self.family,\
                self.given,\
                self.additional,\
                self.prefixes,\
                self.suffixes]))
        return ret

class vC_tel(vC_text):
    "Single Telephone Entry"
    def __init__(self, value="", params=None):
        vC_text.__init__(self, value, params)

        # Set default TEL-Type if not defined:
        if self.params.get("type") is None:
            defaultset = set(vC_tel_types_default)
            self.params.set("type", defaultset)

    def is_pref(self):
        "Is this Entry preferred?"
        return "pref" in self.params.get("type")

class vC_email(vC_text):
    "Single Email Address"
    def __init__(self, value="", params=None):
        vC_text.__init__(self, value, params)

        # Set default EMAIL-Type if not defined:
        if self.params.get("type") is None:
            defaultset = set(vC_email_types_default)
            self.params.set("type", defaultset)

    def is_pref(self):
        "Is this Entry preferred?"
        return "pref" in self.params.get("type")

class vC_adr(vC_AbstractCompoundValue):
    "Single Adress Record"
    def __init__(self, value="", params=None):
        if params is None:
            params = vC_params()
        self.params = params
        # Set default ADR-Type if not defined:
        if self.params.get("type") is None:
            defaultset = set(vC_adr_types_default)
            self.params.set("type", defaultset)
        parts = VALUE_DELIM_RE.split(value)
        self.pobox,\
        self.extended,\
        self.street,\
        self.city,\
        self.region,\
        self.postcode,\
        self.country = gettuple(map(vC_value, parts), 7, vC_value)

    def is_empty(self):
        return False

    def is_pref(self):
        "Is this Entry preferred?"
        return "pref" in self.params.get("type")

    def VCF_repr(self):
        ret = self.params.VCF_repr() + ":"
        ret = ret +  ";".join(map(getvcfrepr, [self.pobox,\
            self.extended,\
            self.street,\
            self.city,\
            self.region,\
            self.postcode,\
            self.country]))
        return ret

    def XML_repr(self):
        ret = "<vCard:Pobox>%s</vCard:Pobox><vCard:Extadd>%s</vCard:Extadd><vCard:Street>%s</vCard:Street>"
        ret = ret + "<vCard:Locality>%s</vCard:Locality><vCard:Region>%s</vCard:Region><vCard:Pcode>%s</vCard:Pcode>"
        ret = ret + "<vCard:Country>%s</vCard:Country>"
        ret = ret % tuple(map(lambda x: x.XML_repr(), [self.pobox,\
            self.extended,\
            self.street,\
            self.city,\
            self.region,\
            self.postcode,\
            self.country]))
        return ret+self.params.XML_repr()

class vC_orgunits(vC_AbstractBaseValue):
    "Contains List of Organizational Units"
    def __init__(self):
        self.list = []

    def get(self):
        return ";".join(self.list)

    def set(self, value):
        if type(value) is ListType:
            self.list = value
        else:
            self.list = map(string.strip, value.split(";"))

    def __repr__(self):
        return "<%s: %s>" % (self.__class__, repr(self.list))

    def is_empty(self):
        return self.list == []

    def VCF_repr(self):
        return ";".join(map(escape, self.list))

    def XML_repr(self):
        ret = "<rdf:seq>"
        for unit in self.list:
            ret = ret + "<rdf:li>%s</rdf:li>" % escapexml(unit)
        return ret+'</rdf:seq>'

class vC_org(vC_AbstractCompoundValue):
    "Organizational Information"
    def __init__(self, value="", params=None):
        if params is None:
            params = vC_params()
        self.params = params
        parts = VALUE_DELIM_RE.split(value)
        self.org = vC_value(getitem(parts, 0, ""))
        self.units = vC_orgunits()
        if len(parts) > 1:
            self.units.list = map(deescape, filter(isNonEmptyLine, parts[1:]))

    def is_empty(self):
        return self.org.get() == "" and self.units.is_empty()

    def VCF_repr(self):
        ret = self.params.VCF_repr() + ":"
        ret = ret + ";".join(map(getvcfrepr, [self.org, self.units]))
        return ret

    def XML_repr(self):
        ret = "<vCard:Orgname>%s</vCard:Orgname><vCard:Orgunit>%s</vCard:Orgunit>"
        ret = ret % tuple(map(lambda x: x.XML_repr(), [self.org, self.units]))
        return ret

# Stores information about last call to getFieldValue():
# _lastreturnedfield = "%d_%s" % (vcard.handle(), fieldname)
_lastreturnedfield = ""
_lastreturnedvalueidx = 0

class vCard:
    """vCard 3.0 Implementation as described in RFC 2426"""
    def _name2attr(self, name):
        return name.lower().replace("-", "_")

    def _attr2name(self, attr):
        return attr.upper().replace("_", "-")

    def __init__(self, block_of_lines=[]):
        self.__dict__["_handle"] = None

        # default values:
        self.__dict__["data"] = {
            "version": vC_text("3.0"),
            "n"     : vC_n(),
            "fn"    : vC_text(),
            "nickname": vC_text(),
            "bday"  : vC_datetime(),
            "tel"   : [],
            "adr"   : [],
            "label" : vC_text(),
            "email" : [],
            "mailer": vC_text(),
            "org"   : vC_org(),
            "title" : vC_text(),
            "role"  : vC_text(),
            "note"  : vC_text(),
            "categories" : vC_categories(),
            "sort_string" : vC_text(),
            "url"   : vC_text(),
            "key"   : vC_text(),
            "rev"   : vC_datetime(time.gmtime()),
            "uid"   : vC_text(),
            # Geographical Types:
            "tz"    : vC_text(),
            "geo"   : vC_geo(),
            # Photographic Picture:
            "photo" : vC_text(),
            # company logo image:
            "logo"  : vC_text()}

        # Name to function mapping:
        self.__dict__["name_func"] = {
            "N"     : vC_n,
            "FN"    : vC_text,
            "NICKNAME": vC_text,
            "BDAY"  : vC_datetime,
            "TEL"   : vC_tel,
            "ADR"   : vC_adr,
            "LABEL" : vC_text,
            "EMAIL" : vC_email,
            "MAILER": vC_text,
            "ORG"   : vC_org,
            "TITLE" : vC_text,
            "ROLE"  : vC_text,
            "NOTE"  : vC_text,
            "CATEGORIES" : vC_categories,
            "SORT-STRING" : vC_text,
            "URL"   : vC_text,
            "KEY"   : vC_text,
            "REV"   : vC_datetime,
            "UID"   : vC_text,
            "TZ"    : vC_text,
            "GEO"   : vC_geo,
            "PHOTO" : vC_text,
            "LOGO"  : vC_text}

        if type(block_of_lines) != ListType:
            # Input was a string?
            # Delete empty lines:
            block_of_lines = filter(isNonEmptyLine, block_of_lines.split('\n'))
            # de-fold:
            makeloglines(block_of_lines)
            block_of_lines = map(vC_contentline, block_of_lines)

        for line in block_of_lines:
            if line.name == "VERSION" and not line.value in SUPPORTED_VERSIONS :
                #XXX: maybe we need to be a little more clever with stdout, but it should
                #     end up in twisted's log
                print "WARNING: Unsupported vCard version (should be \"3.0\" or \"2.1\")."

            self._insertline(line)

        global _lastreturnedvalueidx
        _lastreturnedvalueidx = 0

    def _insertline(self, line):
        if self.name_func.has_key(line.name):
            attr = self._name2attr(line.name)
            if hasattr(self, attr) and type(self.__getattr__(attr)) == ListType:
                # Multi-Value (adr, tel and email):
                self.__getattr__(attr).append(\
                    self.name_func[line.name](line.value, line.params))
            else:
                # Single-Value:
                self.__setattr__(attr,\
                    self.name_func[line.name](line.value, line.params))

    def __getattr__(self, name):
        try:
            return self.data[name]
        except:
            raise AttributeError, "No Attribute '%s'" % (name)

    def __setattr__(self, name, value):
        try:
            self.data[name] = value
        except:
            raise AttributeError, "No Attribute '%s'" % (name)

    def __repr__(self):
        ret = "<%s: " % self.__class__
        for key, value in zip(self.data.keys(), self.data.values()):
            ret = ret + "%s: %s\n" % (repr(key), repr(value)) 
        return ret+">"

    def handle(self):
        return self.__dict__["_handle"]

    def sethandle(self, handle):
        "Handle can be set only once in a lifetime!"
        if self.__dict__["_handle"] == None:
            self.__dict__["_handle"] = handle

    def getSortName(self):
        "usually the same as getDisplayName, differs when sort-string is set"
        return  self.sort_string.get() or\
            self.n.getFamilyGiven() or\
            self.fn.get()

    def getDisplayName(self):
        "Get DisplayName (this is: 'Family, Given' or the FormattedName)"
        return  self.n.getFamilyGiven() or\
            self.fn.get()

    def getFieldValue(self, field_and_idx):
        """Returns content of field as vC_value
           field_and_idx => e.g. 'Street 1'
           return => vC_value or None
           On multiple calls it returns further items from value array
           (Call this functions until it returns None)"""
        global _lastreturnedfield, _lastreturnedvalueidx
        def lastretfieldstr(field, self=self):
            handle = self.handle()
            if handle is None:
                return "None_%s" % (field)
            else:
                return "%d_%s" % (handle, field)
        parts = field_and_idx.split(" ")
        field = parts[0]
        try:
            idx = int(parts[1])-1
        except:
            if  lastretfieldstr(field) == _lastreturnedfield:
                idx = _lastreturnedvalueidx + 1
            else:
                idx = 0
        attr = FIELDNAME2ATTR[field]
        attrobj = getsubattr(self, attr)
        if type(attrobj) == ListType:
            if len(attrobj) > idx:
                    value = attrobj[idx]
            else:
                    value = None
        elif idx >0:
            value = None
        else:
            value = attrobj
        _lastreturnedvalueidx = idx
        _lastreturnedfield = lastretfieldstr(field)
        return value

    def getFieldValueStr(self, field_and_idx, default=""):
        """Returns content of field as string
           field_and_idx => e.g. 'Street 1'
           return => e.g. 'Fifth-Avenue 89'"""
        val = self.getFieldValue(field_and_idx)
        if val:
            return flattenattr(val)
        else:
            # the field does not exist
            # (NOTE: this does not mean empty fields!):
            return default

    def setFieldValueStr(self, field_and_idx, val):
        "Set Field Value"
        parts = field_and_idx.split(" ")
        field = parts[0]
        try:
            idx = int(parts[1])-1
        except:
            idx = 0
        attr = FIELDNAME2ATTR[field]
        attrobj = getsubattr(self, attr)
        if type(attrobj) == ListType:
            if len(attrobj) > idx:
                value = attrobj[idx]
            else:
                # XXX: This is ugly hard-coded!
                if field in ADRFIELDS:
                    self.__getattr__('adr').append(self.name_func['ADR']())
                elif field == 'Phone':
                    self.__getattr__('tel').append(self.name_func['TEL']())
                elif field == 'Email':
                    self.__getattr__('email').append(self.name_func['EMAIL']())
                else:
                    raise ValueError
                attrobj = getsubattr(self, attr)
                value = attrobj[-1]
        elif idx >0:
            raise ValueError
        else:
            value = attrobj
        value.set(val)

    def VCF_repr(self):
        "Native vCard Representation"
        ret = "BEGIN:VCARD\n"
        for name, val in self.data.items():
            if type(val) == ListType:
                for itm in val:
                    ret = ret + log2phylines(self._attr2name(name) + itm.VCF_repr() + "\n")
            elif val != None:
                if not val.is_empty():
                    ret = ret + log2phylines(self._attr2name(name) + val.VCF_repr() + "\n")
        return ret + "END:VCARD\n"

    def XML_repr(self):
        "XML Representation"
        ret = '<rdf:Description rdf:about="%s">\n' % escapexml(self.uid.get())
        for name, val in self.data.items():
            if name != 'version': # We don't need to specify the Version with XML!
                if type(val) == ListType:
                    if len(val) > 1:
                        ret = ret + "<vCard:%s>" % self._attr2name(name)
                        ret = ret + '<rdf:alt>'
                        for itm in val:
                            ret = ret + '<rdf:li>' + itm.XML_repr() + '</rdf:li>'
                        ret = ret + '</rdf:alt>'
                        ret = ret + "</vCard:%s>\n" % self._attr2name(name)
                    elif len(val) > 0:
                        ret = ret + "<vCard:%s>" % self._attr2name(name)
                        ret = ret + val[0].XML_repr()
                        ret = ret + "</vCard:%s>\n" % self._attr2name(name)
                elif val != None:
                    if not val.is_empty():
                        ret = ret + "<vCard:%s>" % self._attr2name(name)
                        ret = ret + val.XML_repr()
                        ret = ret + "</vCard:%s>\n" % self._attr2name(name)
        return ret + "</rdf:Description>\n"


class vCardList:
    """List of vCards"""
    def __init__(self):
        self.handlecounter = 0
        self.data = {}

    def sortedlist(self, sortby=""):
        "Return list of card handles"
        if not sortby:
            sortby = "SortName"
        cards = self.data.values()
        handles = self.data.keys()
        def getfieldvaluestr(card, field=sortby):
            return card.getFieldValueStr(field)
        decorated = zip(map(getfieldvaluestr, cards), handles)
        decorated.sort()
        self.forgetLastReturnedField()
        return [ handle for sortstr, handle in decorated ]

    def LoadFromFile(self, fname):
        "Load from *.vcf file"
        try:
            fd = open(fname, "rb")
            self.LoadFromStream(fd)
            fd.close()
        except:
            return False # Loading failed
        return True

    def LoadFromStream(self, stream, encoding='utf8'):
        "Load from any text stream with file-like methods"
        vCardBlock = None
        lines = stream.readlines()
        makeloglines(lines)

        for line in filter(isNonEmptyLine, lines):
            if type(line) != UnicodeType:
                line = unicode(line, encoding, 'replace')

            line = vC_contentline(line)

            if line.name == "BEGIN" and line.value.upper() == "VCARD":
                vCardName = "default"
                vCardBlock = []

            if vCardBlock == None:
                #XXX: maybe we need to be a little more clever with stdout, but it should
                #     end up in twisted's log
                print "ERROR: Missing 'BEGIN:VCARD' ?"
            else:
                vCardBlock.append(line)

            if line.name == "END" and line.value.upper() == "VCARD":
                self.add(vCard(vCardBlock))

    def SaveToFile(self, fname):
        "Save to *.vcf file"
        fd = open(fname, "wb")
        self.SaveToStream(fd)
        fd.close()

    def SaveToStream(self, stream, encoding='utf8'):
        "Save to Stream (FileDescriptor)"
        stream.write(self.VCF_repr().encode(encoding, 'replace'))

    def __str__(self):
        return str(zip(self.data.keys(), map(str,self.data.values())))

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def clear(self):
        "Removes all vCards"
        self.data.clear()

    def add(self, card=None):
        "Add new vCard to list"
        if card == None:
            card = vCard()
        self.handlecounter += 1
        newhandle = self.handlecounter
        # Handle must not have been set before:
        card.sethandle(newhandle)
        self.data[newhandle] = card
        return newhandle

    def delete(self, handle):
        "Removes vCard with handle from list"
        if self.data.has_key(handle):
            del self.data[handle]
            return True
        else: 
            return False

    def forgetLastReturnedField(self):
        "Reset the lastreturnedfield variable"
        global _lastreturnedfield, _lastreturnedvalueidx
        _lastreturnedfield = ""
        _lastreturnedvalueidx = 0

    def VCF_repr(self):
        "Representation for file output"
        ret = ""
        for card in self.data.values():
            ret = ret + card.VCF_repr() + "\n" # add blank line
        return ret

    def XML_repr(self):
        ret = '<?xml version="1.0"?>\n'
        ret = ret + '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        ret = ret + 'xmlns:vCard="http://www.w3.org/2001/vcard-rdf/3.0#">'
        for card in self.data.values():
            ret = ret + card.XML_repr() + "\n" # add blank line
        return ret + '</rdf:RDF>\n'

