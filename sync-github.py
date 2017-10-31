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
from dystros import utils, version_string

parser = argparse.ArgumentParser()
utils.add_calendar_arguments(parser)

flags = parser.parse_args()

gh = github.MainClass.Github()

state_map = {
        "open": "NEEDS-ACTION",
        "closed": "COMPLETED",
        }

for issue in gh.search_issues(query="assignee:jelmer"):
    props = {'UID': "sync-github-%d" % issue.id,
             "CLASS": "PUBLIC",
             "DESCRIPTION": issue.body,
             "URL": issue.html_url,
             "SUMMARY": issue.title,
             "X-GITHUB-URL": issue.url,
             "STATUS": state_map[issue.state]}
    todo = Todo(**props)

    c = Calendar()
    c.add_component(todo)
    utils.add_member(flags.url, 'text/calendar', c.to_ical())
