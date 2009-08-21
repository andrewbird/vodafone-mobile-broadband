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
Collection of CSV-related utilities and classes
"""
__version__ = "$Rev: 1172 $"

import csv
import codecs
import cStringIO

from wader.common.persistent import Contact

class CSVUnicodeWriter(object):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, csvfile, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = csvfile
        self.encode = codecs.getencoder(encoding)

    def write_row(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.replace('""', '') # remove extra '""'
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encode(data)[0]
        # write to the target stream
        self.stream.write(data)
        self.stream.flush()
        # empty queue
        self.queue.truncate(0)

    def write_rows(self, rows):
        for row in rows:
            self.write_row(row)


class CSVUnicodeReader(object):
    """
    A CSV reader which will iterate over lines in the CSV file fobj,
    which is encoded in the given encoding.
    """

    def __init__(self, fobj, dialect=csv.excel, encoding="utf-8", **kwds):
        self.reader = csv.reader(fobj, dialect=dialect, **kwds)
        self.encoding = encoding

    def next(self):
        """
        Returns a unicode version of C{self.reader.next()}

        This method will probably be overriden in child classes that want
        to customize the class behaviour
        """
        row = self.reader.next()
        return [unicode(s, self.encoding) for s in row]

    def __iter__(self):
        return self

    def get_rows(self):
        """Returns all the rows"""
        return [row for row in self]

class CSVContactsReader(CSVUnicodeReader):

    def __init__(self, fobj, free_ids, dialect=csv.excel,
                 encoding="utf-8", **kwds):
        CSVUnicodeReader.__init__(self, fobj, dialect, encoding, **kwds)
        self.free_ids = free_ids

    def next(self):
        row = self.reader.next()
        name, number = row
        name = unicode(name, self.encoding)
        try:
            index = self.free_ids.popleft()
            return Contact(name, number, index=index)
        except IndexError:
            raise StopIteration

