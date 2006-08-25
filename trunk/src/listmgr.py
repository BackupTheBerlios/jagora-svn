#!/usr/bin/python
# -*- coding: utf-8 -*-
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.
##
##   Contributors:
##     Tomasz Melcer <liori@o2.pl>

''' Main file for discussion groups service. '''

import xmpp

from settings import settings

from connection import Connection

class Service(object):
	def __init__(self):
		''' Load configuration. Connect to the server. Initialize everything. '''
#		self.database = Database(self)
		self.connection = Connection(self)

	def run(self):
		''' Handle requests infinitelly. '''
		while self.connection.handle_incoming_data(1)!=0:
			pass


Service().run()
