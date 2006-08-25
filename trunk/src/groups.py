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
''' Discussion groups service plugin. '''

import xmpp

from settings import settings
from sqlite_db import database, NoSuchGroup

NS_PUBSUB = 'http://jabber.org/protocol/pubsub'
NS_PUBSUB_ERRORS = NS_PUBSUB + '#errors'

def deco(f):
	def d(*a, **b):
		print '%s: %r, %r' % (f.__name__, a, b)
		return f(*a, **b)
	return d

class PubSubError(xmpp.Error):
	''' Helper class to create pubsub-specific error messages. '''
	def __init__(self, node, error, pberror=None, reply=1):
		xmpp.Error.__init__(self, node, error, reply)
		if pberror is not None:
			self.addChild(pberror, namespace=NS_PUBSUB_ERRORS)

class Groups(object, xmpp.PlugIn):
	''' Plugin for component class to handle pubsub requests and create discussion
	groups service. Handles all stanzas related to the service. '''
	def __init__(self, service):
		xmpp.PlugIn.__init__(self)
		DBG_LINE = 'groups'

		self.service = service

	def PlugIn(self, owner, browser, jid=''):
		''' Attach to connection instance. browser needs to be Browser class already
		attached to the same connection. This will set discovery handler for
		given jid, or for all jids if not given. '''
		xmpp.PlugIn.PlugIn(self, owner)

		# register callbacks for iqs with pubsub namespace
		self._owner.RegisterHandler('iq', self.__pubsubCB, 'get', 'http://jabber.org/protocol/pubsub')
		self._owner.RegisterHandler('iq', self.__pubsubCB, 'set', 'http://jabber.org/protocol/pubsub')

		# discovery (set a callback for all nodes (node=''))
		self.disco = browser
		self.jid = jid
		browser.setDiscoHandler(self.__discoveryCB, '', jid)

	def PlugOut(self):
		self.disco.detDiscoHandler('', jid)
		del self.disco
		del self.jid

		xmpp.PlugIn.PlugOut(self)

	def __del__(self):
		if 'disco' in self.__dict__:
			self.PlugOut()

	@deco
	def __discoveryCB(self, conn, request, type):
		node = request.getQuerynode()
		if type == 'info':
			# if node is empty - send disco for service
			if node is None or node == '':
				return {
					'ids': [{
						'category': 'pubsub',
						'type': 'service',
						'name': settings.servicename }],
					'features': [
						xmpp.NS_DISCO_INFO,
						xmpp.NS_DISCO_ITEMS]}
			# otherwise send disco for node
			else:
				# check if the group exists...
				if node not in settings.groups.keys():
					conn.send(xmpp.Error(request, 'item-not-found'))
					raise xmpp.NodeProcessed

				# send group info
				return {
					'ids': [{
						'category': 'pubsub',
						'type': 'leaf',
						'name': settings.groups[node].name }],
					'features': [xmpp.NS_DISCO_INFO]}
		elif type == 'items':
			# check if node is null
			if node is not None and node != '':
				conn.send(xmpp.Error(request, 'feature-not-implemented'))
				raise xmpp.NodeProcessed

			# list existing groups
			items = []
			for gnode, gname, gdesc in database.iter_groups():
				items.append({
					'jid': settings.servicejid,
					'node': gnode,
					'name': gname})

			return items
		else:
			# type must be 'items' or 'info'! Period.
			assert False

	@deco
	def __pubsubCB(self, conn, request):
		''' Dispatcher for pubsub-related iqs. '''
		pubsub = request.getTag('pubsub')

		# pubsub stanzas always have a child element inside pubsub element.
		# we have one callback for each name, that can be found inside
		# pubsub element, so we construct callback name. if there's no
		# such callback, we return do xmpppy; that will mean the requester
		# will get an error from xmpppy

		# this way we won't have to keep table of element names and callbacks,
		# so there will be less code :-). ugly hack, but a table or a series
		# of ifs are worse.

		# because we use private method names (__methodName), we have to
		# add class name to be able to call them (_Groups__methodName).

		for child in pubsub.getChildren():
			if not isinstance(child, xmpp.Node): continue
			print child.getName()
			callbackname = '_Groups__pubsub'+child.getName().capitalize()+'CB'
			print callbackname

			try:
				callback = self.__getattribute__(callbackname)
			except AttributeError:
				return

			callback(conn, request, child)
			return

	@deco
	def __pubsubSubscribeCB(self, conn, request, subscribe):
		''' Called when user wants to subscribe to node. '''
		# bare jids
		fromjid = xmpp.JID(request.getFrom()).getStripped()
		subsjid = xmpp.JID(subscribe.getAttr('jid')).getStripped()

		# checking if the client want to subscribe himself... (bare jids!)
		if fromjid != subsjid:
			conn.send(PubSubError(request, 'bad-request', 'invalid-jid'))
			raise xmpp.NodeProcessed

		# ok, so the client can subscribe to the node... do so
		node = subscribe.getAttr('node')
		try:
			# do the db work
			database.add_subscriber(node, fromjid)

			# and send reply
			reply = request.buildReply('result')
			element = reply.addChild('pubsub', namespace=NS_PUBSUB)
			element = element.addChild('subscription', {
				'node': node,
				'jid': fromjid,
				'subscription': 'subscribed'})

			conn.send(reply)
			raise xmpp.NodeProcessed
		except NoSuchGroup:
			# group does not exists? send an error...
			conn.send(PubSubError(request, 'item-not-found'))
			raise xmpp.NodeProcessed

	@deco
	def __pubsubUnsubscribeCB(self, conn, request, unsubscribe):
		''' Called when user wants to unsubscribe from node. '''
		fromjid = xmpp.JID(request.getFrom()).getStripped()
		subsjid = xmpp.JID(unsubscribe.getAttr('jid')).getStripped()

		# checking if the client want to unsubscribe himself...
		if fromjid != subsjid:
			conn.send(PubSubError(request, 'bad-request', 'invalid-jid'))
			raise xmpp.NodeProcessed

		groupid = unsubscribe.getAttr('node')
		# ok, so the client can unsubscribe from the node... do so
		try:
			database.remove_subscriber(groupid, fromjid)
			
			# and send reply
			reply = request.buildReply('result')

			conn.send(reply)

			raise xmpp.NodeProcessed
		except NoSuchGroup:
			conn.send(PubSubError(request, 'item-not-found'))
			raise xmpp.NodeProcessed
		

	@deco
	def __pubsubSubscriptionsCB(self, conn, request, subscriptions):
		''' Called when user wants to get his subscription list. '''
		# bare jid of entity
		fromjid = xmpp.JID(request.getFrom()).getStripped()

		# JEP says we should return an error when there is no subscriptions,
		# but seems that returning empty list will be soon legal too;
		# that's easier ;-)

		reply = request.buildReply('result')
		element = reply.addChild('pubsub', namespace=NS_PUBSUB)
		element = element.addChild('subscriptions')

		for node in database.iter_subscriptions(fromjid):
			element.addChild('subscription', {
				'node': node,
				'jid': fromjid,
				'subscription': 'subscribed'})

		conn.send(reply)

		raise xmpp.NodeProcessed

	@deco
	def __pubsubPublishCB(self, conn, request, publish):
		''' Called when user want to publish new item. '''
		# bare jid of entity
		fromjid = xmpp.JID(request.getFrom()).getStripped()
		groupid = publish['node']

		print groupid

		# check error conditions
		# is this jid subscribed? (actually this doesn't make any sense, as
		# anybody can subscribe; but later it will be necessary)
		if not database.is_subscribed(groupid, fromjid):
			conn.send(PubSubError(request, 'error'))
			raise xmpp.NodeProcessed

		# parse the item and fill missing data
		olditem = publish.getTag('item').getTag('entry')

		stanza = xmpp.Message(subject=olditem.getTagData('title'),
			body='From: %s (%s)\n\n%s' % (
				olditem.getTag('author').getTagData('name'),
				fromjid,
				olditem.getTagData('content')))

		item = stanza.addChild('entry', namespace='http://www.w3.org/2005/Atom')
		author = item.addChild('author')
		author.addChild('name', {}, [olditem.getTag('author').getTagData('name')])
		author.addChild('jid', {}, [fromjid])

		item.addChild('generator', {}, [olditem.getTagData('generator')])
		item.addChild('id', {}, [olditem.getTagData('id')])
		item.addChild('category', {'term': groupid})
		item.addChild('content', {}, [olditem.getTagData('content')])
		item.addChild('title', {}, [olditem.getTagData('title')])

		for subscriber in database.iter_subscribers(groupid):
			stanza.setTo(subscriber)
			conn.send(stanza)

		raise xmpp.NodeProcessed
