#!/usr/bin/python3
# Example usage: ./current-user-principal.py --url=https://www.jelmer.uk/dav/jelmer/calendars/blah

from dystros import caldav, utils

import optparse

parser = optparse.OptionParser("current-user-principal")
parser.add_option_group(utils.CalendarOptionGroup(parser))
opts, args = parser.parse_args()

cup = caldav.get_current_user_principal(opts.url)
inbox_url = utils.get_inbox_url(cup))
