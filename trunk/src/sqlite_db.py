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
''' Sqlite backend to store subscriptions and old messages. Needs sqlite 3.3.0. '''

from pysqlite2 import dbapi2 as sqlite

from settings import settings

class NoSuchGroup: pass

class Database:
	def __init__(self):
		''' Connect to the database. If the db does not exist,
		create it.'''
		self.db = sqlite.connect(settings.sqlite_filename)

		# create appropriate tables if they does not exist
		self.cur = self.db.cursor()

		# this will create database structure. will fail silently if the tables
		# are already there
		try:
			self.cur.executescript('''
				CREATE TABLE groups (node TEXT PRIMARY KEY, name TEXT, description TEXT);
				CREATE TABLE subscriptions (node TEXT, jid TEXT, UNIQUE (node, jid));
			''');
			self.db.commit()
		except sqlite.OperationalError:
			pass

		# this will get data from settings, when there's something to add...
		settings.syncWithDB(self)

	def add_subscriber(self, node, jid):
		''' If the appropriate data doesn't exist in the table already, we check if
		there is group with node 'node' and add information about new subscriber. '''
		self.cur.execute('''SELECT node FROM groups WHERE node=? LIMIT 1''', (node,))
		if len(self.cur.fetchall())<1:
			# we don't have such group...
			raise NoSuchGroup

		self.cur.execute('''INSERT OR IGNORE INTO subscriptions VALUES (?, ?)''', (node, jid))

	def remove_subscriber(self, node, jid):
		''' Remove any information about jid subscribing to node. '''
		self.cur.execute('''
			DELETE FROM subscriptions WHERE node=? AND jid=?''', (node, jid))

	def is_subscribed(self, node, jid):
		''' Check if jid is subscribed to node. '''
		self.cur.execute('''SELECT node FROM subscriptions WHERE node=? AND jid=?''', (node, jid))
		return len(self.cur.fetchall())>0

	def add_group(self, node, name, desc):
		''' Adds a group to the list, only if the node is not used yet. '''
		self.cur.execute('''
			INSERT INTO groups VALUES (?, ?, ?)''', (node, name, desc))

	def add_or_edit_group(self, node, name, desc):
		''' Adds a group to the list, or edits group info. '''
		self.cur.execute('''
			INSERT OR REPLACE INTO groups VALUES (?, ?, ?)''', (node, name, desc))

	def remove_group(self, node):
		''' Remove any information about group with given node. Remove all its subscribers. '''
		pass

	def iter_subscriptions(self, jid):
		''' Iterate over subscriptions for given jid. '''
		self.cur.execute('''
			SELECT node FROM subscriptions WHERE jid=?''', (jid,))

		for node, in self.cur:
			yield node

	def iter_subscribers(self, node):
		''' Iterate over subscribers for given node. '''
		self.cur.execute('''
			SELECT jid FROM subscriptions WHERE node=?''', (node,))

		for jid, in self.cur:
			yield jid

	def iter_groups(self):
		''' Iterate over existing groups. '''
		self.cur.execute('''
			SELECT * FROM groups''')

		for node, name, desc in self.cur:
			yield node, name, desc

database = Database()
