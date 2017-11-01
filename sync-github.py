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
    props = {'UID': issue.url,
             "CLASS": "PUBLIC",
             "DESCRIPTION": issue.body,
             "URL": issue.html_url,
             "SUMMARY": issue.title,
             "X-GITHUB-URL": issue.url,
             "STATUS": state_map[issue.state]}
    if issue.milestone and issue.milestone.url:
        props["X-MILESTONE"] = issue.milestone.url
    if issue.created_at:
        props["CREATED"] = vDatetime(issue.created_at)
    if issue.closed_at:
        props["COMPLETED"] = vDatetime(issue.closed_at)
    for label in issue.labels:
        props["X-LABEL"] = label.name
    todo = Todo(**props)

    c = Calendar()
    c.add_component(todo)
    try:
        (href, etag, old) = utils.get_by_uid(flags.url, "VTODO", props["UID"])
    except KeyError:
        print("Adding todo item for %r" % issue.title)
        utils.add_member(flags.url, 'text/calendar', c.to_ical())
    else:
        if_match = [etag]
        url = urllib.parse.urljoin(flags.url, href)
        if c.to_ical() != old:
            print("Updating todo item for %r" % issue.title)
            utils.put(url, 'text/calendar', c.to_ical(), if_match=if_match)
