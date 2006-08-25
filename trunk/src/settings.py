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
''' Settings for listmgr service. To use:
from settings import settings
'''

import ConfigParser
import sys

# please dont touch next line and the line with ending bracket, and keep the same format
# in every line - this will be used to generate documentation
#
# None means that this field is not automatically generated from config, there's special code
# to load it
global_settings = (
	('server', str),	# server to connect to (eg. 'localhost')
	('port', int),		# port number (eg. 5553)
	('servicejid', str),	# jid of the service (eg. 'groups.localhost')
	('password', str),	# password (eg. 'passwd')

	('servicename', str),	# name of service, that will be visible in discovery (eg. 'Discussion Groups')

	('sqlite_filename', str), # file name of database to use (file will be created when doesn't exist);
				# when string ":memory:" is used, the database will be kept in memory
				# and will not be saved to filesystem!
)

group_settings = (
	('id', None),		# 
	('name', str),		# human-readable name of group (eg. 'Test group')
	('description', str),	# human-readable long description of the group (eg. 'Place to test new clients.')
)

class Group(object):
	''' Simple class to store group metadata. Filled with info by Settings class. '''
	pass

class Settings(object):
	''' This class keeps settings for service. It comes from several resources:
	command line, configuration files, database.
	
	Main option values are kept as member values in the instance itself,
	for group options use instance['group-name'].option mantra.

	Options are described above, in the definitions of global_settings and
	group_settings.'''
	def __init__(self):
		''' Load the configuration from standard locations. '''
		self.parseCommandLine()
		self.loadFromFiles(['/etc/listmgr.cfg', 'listmgr.cfg'] + sys.argv[1:])

	def parseCommandLine(self):
		# TODO
		pass

	def loadFromFiles(self, filenames):
		''' Part of configuration is kept read-only in files. That includes
		xmpp connection data, database connection data, initial groups configuration. '''
		parser = ConfigParser.SafeConfigParser()
		parser.read(filenames)

		# get the 'global' settings
		# TODO: try:
		for name, type in global_settings:
			if type is str:
				self.__dict__[name] = parser.get('DEFAULT', name)
			elif type is int:
				self.__dict__[name] = parser.getint('DEFAULT', name)
			elif type is None:
				pass
			else:
				assert False
		# TODO: nice error handlers
		#except ValueError:
		#except ConfigParser.NoOptionError:

		# get the settings for each group
		self.groups = {}
		for node in parser.sections():
			g = Group()
			g.node = node
			for name, type in group_settings:
				if type is str:
					g.__dict__[name] = parser.get(node, name)
				elif type is int:
					g.__dict__[name] = parser.getint(node, name)
				elif type is None:
					pass
				else:
					assert False

			self.groups[node] = g

	def syncWithDB(self, db):
		''' This will add groups that are not yet in the database, but were
		mentioned in the config files or in the commandline, and apply
		command line arguments such as group metadata modification. 
		
		After that we discard group data from this object, as everything
		is in database.'''

		for group in self.groups.itervalues():
			db.add_or_edit_group(group.node, group.name, group.description)

		del self.groups

# global instance created
settings = Settings()
