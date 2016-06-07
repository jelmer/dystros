#!/usr/bin/python
#
# Dystros
# Copyright (C) 2016 Jelmer Vernooij <jelmer@jelmer.uk>
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
import sys
from wsgiref.simple_server import make_server

sys.path.insert(0, os.path.dirname(__file__))

from dystros.server import DystrosApp
app = DystrosApp()

httpd = make_server('', 8000, app)
print "Serving HTTP on port 8000..."

# Respond to requests until process is killed
httpd.serve_forever()
