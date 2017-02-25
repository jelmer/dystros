# encoding: utf-8
#
# Dystros
# Copyright (C) 2016 Jelmer Vernooĳ <jelmer@jelmer.uk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) any later version of
# the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

import os

from configobj import ConfigObj

from xdg.BaseDirectory import xdg_config_home

def GetConfig():
    config_dir_path = os.path.join(xdg_config_home, 'dystros')
    os.makedirs(config_dir_path, exist_ok=True)
    config_file_path = os.path.join(config_dir_path, 'config')
    return ConfigObj(config_file_path, create_empty=True)
