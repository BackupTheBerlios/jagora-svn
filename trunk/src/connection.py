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

import xmpp

from settings import settings
from groups import Groups

class Connection(object):
	def __init__(self, service):
		''' Initiate the connection. Make a connect, then plug in browser.'''
		self.service = service

		self.xmpp = xmpp.Component(settings.servicejid, port=settings.port)
		self.xmpp.connect((settings.server, settings.port))
		self.xmpp.auth(settings.servicejid, settings.password)

		self.disco = xmpp.browser.Browser()
		self.disco.PlugIn(self.xmpp)

		self.groups = Groups(self.service)
		self.groups.PlugIn(self.xmpp, self.disco)

	def handle_incoming_data(self, timeout=0):
		''' Handle data that came since last execution. When timeout given,
		block for that many seconds. '''
		self.xmpp.Process(timeout)
