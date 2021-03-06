#!/usr/bin/python3
# encoding: utf-8
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



import hashlib
import logging
import optparse
import urllib.request, urllib.parse, urllib.error
import os
from icalendar.cal import Calendar
from icalendar.prop import vUri, vText
import sys

from dystros import caldav, utils

def StripStamps(c):
    if c is None:
        return None
    c = Calendar.from_ical(c.to_ical())
    for sc in c.subcomponents:
        if 'DTSTAMP' in sc:
            del sc['DTSTAMP']
    return c.to_ical()


def hasChanged(a, b):
    return StripStamps(a) != StripStamps(b)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stderr)
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(levelname)s: %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)

parser = optparse.OptionParser("split")
parser.add_option_group(utils.CalendarOptionGroup(parser))
parser.add_option("--invite", dest="invite", action="store_true", help="Store as invite.")
parser.add_option("--prefix", dest="prefix", default="unknown", help="Filename prefix")
parser.add_option('--category', dest='category', default=None, help="Category to add.")
parser.add_option('--status', dest='status', type="choice", choices=["", "tentative", "confirmed"], default=None, help="Status to set.")
opts, args = parser.parse_args()

cup = caldav.get_current_user_principal(opts.url)
logging.info('Current user principal: %s', cup)
inbox_url = utils.get_inbox_url(cup)
logging.info('Inbox URL: %s', inbox_url)

if opts.invite:
    target_collection_url = inbox_url
else:
    target_collection_url = opts.url

try:
    import_url = args[0]
except IndexError:
    f = sys.stdin.buffer
    import_url = None
else:
    f = urllib.request.urlopen(import_url)

orig = Calendar.from_ical(f.read())

other = []
items = {}
for component in orig.subcomponents:
    if component.name in ('VEVENT', 'VTODO'):
        try:
            items[component['UID']] = component
        except KeyError:
            raise KeyError('missing UID for %s in %s' % (component.name, url))
    else:
        other.append(component)

seen = 0
changed = 0
added = 0
for (uid, ev) in items.items():
    seen += 1
    (old, todo, new, href, etag, ev) = utils.create_or_update_calendar_item(
        target_collection_url, "VEVENT", uid)
    out = Calendar()
    if import_url is not None:
        out['X-IMPORTED-FROM-URL'] = vUri(import_url)
    # If this is not an iTIP request, then make it one.
    if "METHOD" not in out and opts.invite:
        out["METHOD"] = "REQUEST"
    out.update(list(orig.items()))
    for c in other:
        out.add_component(c)
    if opts.category:
        if isinstance(ev.get('CATEGORIES', ''), vText):
            ev['CATEGORIES'] = [ev['CATEGORIES']]
        ev.setdefault('categories', []).append(vText(opts.category))
    if opts.status and 'STATUS' not in ev:
        ev['STATUS'] = opts.status.upper()
    out.add_component(ev)
    write = hasChanged(old, out)
    if write:
        if old is None:
           added += 1
           utils.add_member(target_collection_url, 'text/calendar', out.to_ical())
        else:
           changed += 1
           utils.put(href, 'text/calendar', out.to_ical(), if_match=[etag])

logger.info('Processed %s. Seen %d, updated %d, new %d', opts.prefix,
             seen, changed, added)
