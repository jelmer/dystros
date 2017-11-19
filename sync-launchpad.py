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
from dystros import utils, version_string
import urllib.parse

parser = argparse.ArgumentParser()
utils.add_calendar_arguments(parser)

flags = parser.parse_args()

launchpad = Launchpad.login_anonymously(
        'dystros', 'production',
        os.path.join(xdg_cache_home, 'dystros'), version='devel')


for task in launchpad.bugs.searchTasks(assignee=launchpad.me):
    try:
        (href, etag, old) = utils.get_by_uid(flags.url, "VTODO", task.self_link)
    except KeyError:
        etag = None
        props = {'UID': task.self_link, "CLASS": "PUBLIC"}
        todo = Todo(**props)
        new = Calendar()
        new.add_component(todo)
    else:
        new = Calendar.from_ical(old.to_ical())
        for component in old.subcomponents:
            if component.name == "VTODO":
                todo = component
                break

    todo["URL"] = task.web_link
    todo["SUMMARY"] = "%s: %s" % (task.target.name, task.bug.title)

    if task.is_completed:
        todo["STATUS"] = "COMPLETED"
    else:
        todo["STATUS"] = "NEEDS-ACTION"

    if task.date_created:
        todo["CREATED"] = vDatetime(task.date_created)
    if task.date_closed:
        todo["COMPLETED"] = vDatetime(task.date_closed)

    # TODO(jelmer): Set RELATED-TO (SIBLING) based on task.related_tasks

    # TODO(jelmer): Set COMMENT field based on task.messages

    todo["CATEGORIES"] = task.bug.tags.split(',')

    todo["DESCRIPTION"] =  task.bug.description

    if etag is None:
        print("Adding todo item for %r" % task.self_link)
        utils.add_member(flags.url, 'text/calendar', new.to_ical())
    else:
        if_match = [etag]
        url = urllib.parse.urljoin(flags.url, href)
        if new != old:
            print("Updating todo item for %r" % task.bug.title)
            utils.put(url, 'text/calendar', new.to_ical(), if_match=if_match)
