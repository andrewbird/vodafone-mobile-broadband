# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
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
setuptools file for Vodafone Mobile Broadband.
"""

import sys
from os import listdir, makedirs
from os.path import basename, exists, join, isdir, walk
from glob import glob
from subprocess import call

from setuptools import setup

from distutils.command.install_data import install_data as _install_data
from distutils import cmd
from distutils.command.build import build as _build

from wader.vmb.consts import (APP_VERSION, APP_NAME,
                              RESOURCES_DIR)

BIN_DIR = '/usr/bin'
APPLICATIONS = '/usr/share/applications'
PIXMAPS = '/usr/share/pixmaps'
DBUS_SYSTEMD = '/etc/dbus-1/system.d'


def paint_file(path, text):
    from PIL import Image, ImageFont, ImageDraw
    im = Image.open(path)
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype("resources/tools/FreeSans.ttf", 12)
    draw.text((300, 0), text, font=font)
    im.save(path)


class build_trans(cmd.Command):

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for filename in glob(join('.', 'resources', 'po', '*.po')):
            lang = basename(filename)[:-3]

            tdir = join('build', 'locale', lang, 'LC_MESSAGES')
            if not exists(tdir):
                makedirs(tdir)

            tfil = join(tdir, 'vodafone-mobile-broadband.mo')
            call(['msgfmt', '-cf', '-o', tfil, filename])

#        raise RuntimeError("Uncomment to stop and see translation errors easily")


class build(_build):
    sub_commands = _build.sub_commands + [('build_trans', None)]

    def run(self):
        _build.run(self)


class install_data(_install_data):

    def run(self):
        for lang in listdir('build/locale/'):
            lang_dir = join('share', 'locale', lang, 'LC_MESSAGES')
            lang_file = join('build', 'locale', lang, 'LC_MESSAGES', 'vodafone-mobile-broadband.mo')
            self.data_files.append((lang_dir, [lang_file]))

        _install_data.run(self)

        for outfile in self.outfiles:
            if 'splash.png' in outfile:
                paint_file(outfile, APP_VERSION)


def list_files(path, exclude=None):
    result = []

    def walk_callback(arg, directory, files):
        for ext in ['.svn', '.git']:
            if ext in files:
                files.remove(ext)
        if exclude:
            for file in files:
                if file.startswith(exclude):
                    files.remove(file)
        result.extend(join(directory, file) for file in files
                      if not isdir(join(directory, file)))

    walk(path, walk_callback, None)
    return result

data_files = [
   (join(RESOURCES_DIR, 'glade'), list_files('resources/glade')),
   (join(RESOURCES_DIR, 'glade/animation'),
        list_files('resources/glade/animation')),
   (join(RESOURCES_DIR, 'themes'), list_files('resources/themes')),
   (BIN_DIR, ['bin/vodafone-mobile-broadband']),
]

if sys.platform == 'linux2':
    append = data_files.append
    append((APPLICATIONS, ['resources/desktop/vodafone-mobile-broadband.desktop']))
    append((PIXMAPS, ['resources/desktop/vodafone-mobile-broadband.png']))
    append((DBUS_SYSTEMD, ['resources/dbus/vodafone-mobile-broadband.conf']))


packages = [
    'wader.vmb',
    'wader.vmb.models',
    'wader.vmb.controllers',
    'wader.vmb.views',
    'wader.vmb.contacts',
    'wader.vmb.contrib',
    'wader.vmb.contrib.pycocuma',
    'wader.vmb.contrib.gtkmvc',
    'wader.vmb.contrib.gtkmvc.adapters',
    'wader.vmb.contrib.gtkmvc.progen',
    'wader.vmb.contrib.gtkmvc.support',
]

cmdclass = {
    'build': build,
    'build_trans': build_trans,
    'install_data': install_data,
}

setup(name=APP_NAME,
      version=APP_VERSION,
      description='3G device manager for Linux',
      download_url="http://public.warp.es/wader",
      author='Pablo Martí Gamboa',
      author_email='pmarti@warp.es',
      license='GPL',
      packages=packages,
      data_files=data_files,
      cmdclass=cmdclass,
      zip_safe=False,
      test_suite='wader.test',
      classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Topic :: Communications :: Telephony',
      ])
