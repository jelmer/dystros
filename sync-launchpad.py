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


from launchpadlib.launchpad import Launchpad

from xdg.BaseDirectory import xdg_cache_home

import argparse
from icalendar.cal import Calendar, Todo
from icalendar.prop import vDatetime
import os
from dystros import utils, version_string
import urllib.parse

parser = argparse.ArgumentParser()
utils.add_calendar_arguments(parser)

flags = parser.parse_args()

launchpad = Launchpad.get_token_and_login(
        'dystros', 'production',
        os.path.join(xdg_cache_home, 'dystros'))

STATUSES = [
    'New',
    'Incomplete',
    'Confirmed',
    'Triaged',
    'In Progress',
    'Fix Committed',
    'Fix Released',
    'Won\'t Fix',
]

for task in launchpad.bugs.searchTasks(assignee=launchpad.me, status=STATUSES):
    print("Processing %s" % task.bug.id)
    (old, new, href, etag, todo) = utils.create_or_update_calendar_item(flags.url, "VTODO", task.self_link)
    todo["CLASS"] = "PUBLIC"
    todo["URL"] = task.web_link
    todo["SUMMARY"] = "%s: %s" % (task.target.name, task.bug.title)

    if task.is_complete:
        todo["STATUS"] = "COMPLETED"
    else:
        todo["STATUS"] = "NEEDS-ACTION"

    if task.date_created and False:
        todo["CREATED"] = vDatetime(task.date_created)
    if task.date_closed and False:
        todo["COMPLETED"] = vDatetime(task.date_closed)

    # TODO(jelmer): Set RELATED-TO (SIBLING) based on task.related_tasks

    # TODO(jelmer): Set COMMENT field based on task.messages

    todo["CATEGORIES"] = task.bug.tags

    todo["DESCRIPTION"] =  task.bug.description

    if etag is None:
        print("Adding todo item for %r" % task.self_link)
        utils.add_member(flags.url, 'text/calendar', new.to_ical())
    else:
        url = urllib.parse.urljoin(flags.url, href)
        if new.to_ical() != old.to_ical():
            print("Updating todo item for %r" % task.bug.title)
            utils.put(url, 'text/calendar', new.to_ical(), if_match=[etag])
