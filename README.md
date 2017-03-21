[![Build Status](https://travis-ci.org/jelmer/dystros.png?branch=master)](https://travis-ci.org/jelmer/dystros)

Dystros is a set of command-line utilities for working with calendars and
addressbooks over CalDAV/CardDAV.

Dystros (Δύστρος) takes its name from the name of the February month in the ancient
Macedonian calendar, used in Macedon in the first millennium BC.

It's mostly a collection of scripts related to ics for my personal use, but
some scripts may be useful for others.

Tools
=====

It comes with the following tools:

 * freebusy.py - Run freebusy-query against a DAV server
 * fix-songkick.py - Strip boilerplate from songkick.com ics files
 * prinday.py - Print events for a single day
 * printcalendar.py - Print the full list of upcoming events
 * newtravel.py - Create new travel event
 * split.py - Import an .ics file, putting each VEVENT into its own file.
 * travel.py - Print all events with category 'Travel'
 * todo.py - Print all todo items
