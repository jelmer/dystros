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


import github

import argparse
from icalendar.cal import Calendar, Todo
from icalendar.prop import vDatetime
from dystros import utils, version_string
import urllib.parse

parser = argparse.ArgumentParser()
utils.add_calendar_arguments(parser)

flags = parser.parse_args()

gh = github.MainClass.Github()

state_map = {
        "open": "NEEDS-ACTION",
        "closed": "COMPLETED",
        }

for issue in gh.search_issues(query="assignee:jelmer"):
    try:
        (href, etag, old) = utils.get_by_uid(flags.url, "VTODO", issue.url)
    except KeyError:
        etag = None
        props = {'UID': issue.url, "CLASS": "PUBLIC"}
        todo = Todo(**props)
        new = Calendar()
        new.add_component(todo)
    else:
        new = Calendar.from_ical(old.to_ical())
        for component in old.subcomponents:
            if component.name == "VTODO":
                todo = component
                break

    todo["DESCRIPTION"] =  issue.body,
    todo["URL"] = issue.html_url
    todo["SUMMARY"] = "%s: %s" % (issue.repository.name, issue.title)
    todo["X-GITHUB-URL"] = issue.url
    todo["STATUS"] = state_map[issue.state]
    if issue.milestone and issue.milestone.url:
        todo["X-MILESTONE"] = issue.milestone.url
    if issue.created_at:
        todo["CREATED"] = vDatetime(issue.created_at)
    if issue.closed_at:
        todo["COMPLETED"] = vDatetime(issue.closed_at)
    for label in issue.labels:
        todo["X-LABEL"] = label.name

    if etag is None:
        print("Adding todo item for %r" % issue.title)
        utils.add_member(flags.url, 'text/calendar', new.to_ical())
    else:
        if_match = [etag]
        url = urllib.parse.urljoin(flags.url, href)
        if new != old:
            print("Updating todo item for %r" % issue.title)
            utils.put(url, 'text/calendar', new.to_ical(), if_match=if_match)
