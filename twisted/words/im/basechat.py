# -*- test-case-name: twisted.words.test.test_basechat -*-
# Copyright (c) 2001-2010 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Base classes for Instance Messenger clients.
"""

from twisted.words.im.locals import OFFLINE, ONLINE, AWAY


class ContactsList:
    """
    A GUI object that displays a contacts list.

    @param chatui: The GUI chat client associated with this contacts list.
    @type chatui: L{ChatUI}

    @param contacts: The contacts.
    @type contacts: L{dict} mapping C{str} to an implementer of
        L{Person<interfaces.IPerson>}

    @param onlineContacts: The contacts who are currently online (have a status
        that is not L{locals.OFFLINE}).
    @type onlineContacts: L{dict} mapping C{str} to an implementer of
        L{Person<interfaces.IPerson>}

    @param clients: The signed-on clients.
    @type clients: L{list} of implementers of L{Client<interfaces.IClient>}
    """
    def __init__(self, chatui):
        """
        @param chatui: The GUI chat client associated with this contact list.
        @type chatui: L{ChatUI}
        """
        self.chatui = chatui
        self.contacts = {}
        self.onlineContacts = {}
        self.clients = []


    def setContactStatus(self, person):
        """
        Inform the user that a person's status has changed.

        @param person: The person whose status has changed.
        @type person: L{Person<interfaces.IPerson>}
        """
        if not self.contacts.has_key(person.name):
            self.contacts[person.name] = person
        if not self.onlineContacts.has_key(person.name) and \
            (person.status == ONLINE or person.status == AWAY):
            self.onlineContacts[person.name] = person
        if self.onlineContacts.has_key(person.name) and \
           person.status == OFFLINE:
            del self.onlineContacts[person.name]


    def registerAccountClient(self, client):
        """
        Notify the user that an account client has been signed on to.

        @param client: The client being added to your list of account clients.
        @type client: L{Client<interfaces.IClient>}
        """
        if not client in self.clients:
            self.clients.append(client)


    def unregisterAccountClient(self, client):
        """
        Notify the user that an account client has been signed off or
        disconnected from.

        @param client: The client being removed from the list of account
            clients.
        @type client: L{Client<interfaces.IClient>}
        """
        if client in self.clients:
            self.clients.remove(client)


    def contactChangedNick(self, person, newnick):
        """
        Update your contact information to reflect a change to a contact's
        nickname.

        @param person: The person in your contacts list whose nickname is
            changing.
        @type person: L{Person<interfaces.IPerson>}

        @param newnick: The new nickname for this person.
        @type newnick: C{str}
        """
        oldname = person.name
        if self.contacts.has_key(oldname):
            del self.contacts[oldname]
            person.name = newnick
            self.contacts[newnick] = person
            if self.onlineContacts.has_key(oldname):
                del self.onlineContacts[oldname]
                self.onlineContacts[newnick] = person



class Conversation:
    """
    A GUI window of a conversation with a specific person.

    @ivar person: The person who you're having this conversation with.
    @type person: L{Person<interfaces.IPerson>}

    @ivar chatui: The GUI chat client associated with this conversation.
    @type chatui: L{ChatUI}
    """
    def __init__(self, person, chatui):
        """
        @param person: The person who you're having this conversation with.
        @type person: L{Person<interfaces.IPerson>}

        @param chatui: The GUI chat client associated with this conversation.
        @type chatui: L{ChatUI}
        """
        self.chatui = chatui
        self.person = person


    def show(self):
        """
        Displays the ConversationWindow
        """
        raise NotImplementedError("Subclasses must implement this method")


    def hide(self):
        """
        Hides the ConversationWindow
        """
        raise NotImplementedError("Subclasses must implement this method")


    def sendText(self, text):
        """
        Send text to the person with whom the user is conversing.

        @param text: The text to be sent.
        @type text: C{str}

        @rtype: L{Deferred<twisted.internet.defer.Deferred>}
        """
        self.person.sendMessage(text, None)


    def showMessage(self, text, metadata=None):
        """
        Display a message sent from the person with whom the user is conversing.

        @param text: The sent message.
        @type text: C{str}

        @param metadata: Metadata associated with this message.
        @type metadata: C{dict}
        """
        raise NotImplementedError("Subclasses must implement this method")


    def contactChangedNick(self, person, newnick):
        """
        Change a person's name.

        @param person: The person whose nickname is changing.
        @type person: L{Person<interfaces.IPerson>}

        @param newnick: The new nickname for this person.
        @type newnick: C{str}
        """
        self.person.name = newnick



class GroupConversation:
    """
    A GUI window of a conversation with a group of people.

    @ivar chatui: The GUI chat client associated with this conversation.
    @type chatui: L{ChatUI}

    @ivar group: The group of people that are having this conversation.
    @type group: Implementer of L{Group<interfaces.IGroup>}

    @ivar members: The names of the people in this conversation.
    @type members: C{list} of C{str}
    """
    def __init__(self, group, chatui):
        """
        @param chatui: The GUI chat client associated with this conversation.
        @type chatui: L{ChatUI}

        @param group: The group of people that are having this conversation.
        @type group: Implementer of L{Group<interfaces.IGroup>}
        """
        self.chatui = chatui
        self.group = group
        self.members = []


    def show(self):
        """
        Displays the GroupConversationWindow.
        """
        raise NotImplementedError("Subclasses must implement this method")


    def hide(self):
        """
        Hides the GroupConversationWindow.
        """
        raise NotImplementedError("Subclasses must implement this method")


    def sendText(self, text):
        """
        Sends text to the group.

        @param: The text to be sent.
        @type text: C{str}

        @rtype: L{Deferred<twisted.internet.defer.Deferred>}
        """
        self.group.sendGroupMessage(text, None)


    def showGroupMessage(self, sender, text, metadata=None):
        """
        Displays to the user a message sent to this group from the given sender.

        @param sender: The person sending the message.
        @type sender: C{str}

        @param text: The sent message.
        @type text: C{str}

        @param metadata: Metadata associated with this message.
        @type metadata: C{dict}
        """
        raise NotImplementedError("Subclasses must implement this method")


    def setGroupMembers(self, members):
        """
        Sets the list of members in the group.

        @param members: The names of the people that will be in this group.
        @type members: C{list} of C{str}
        """
        self.members = members


    def setTopic(self, topic, author):
        """
        Changes the topic for the group conversation window and display this
        change to the user.

        @param: This group's topic.
        @type topic: C{str}

        @param author: The person changing the topic.
        @type author: C{str}
        """
        raise NotImplementedError("Subclasses must implement this method")


    def memberJoined(self, member):
        """
        Adds the given member to the list of members in the group conversation
        and displays this to the user.

        @param member: The person joining the group conversation.
        @type member: C{str}
        """
        if not member in self.members:
            self.members.append(member)


    def memberChangedNick(self, oldnick, newnick):
        """
        Changes the nickname for a member of the group conversation and displays
        this change to the user.

        @param oldnick: The old nickname.
        @type oldnick: C{str}

        @param newnick: The new nickname.
        @type newnick: C{str}
        """
        if oldnick in self.members:
            self.members.remove(oldnick)
            self.members.append(newnick)


    def memberLeft(self, member):
        """
        Deletes the given member from the list of members in the group
        conversation and displays the change to the user.

        @param member: The person leaving the group conversation.
        @type member: C{str}
        """
        if member in self.members:
            self.members.remove(member)



class ChatUI:
    """
    A GUI chat client.

    @type conversations: C{dict} of L{Conversation}.
    @ivar conversations: A cache of all the direct windows.

    @type groupConversations: C{dict} of L{GroupConversation}.
    @ivar groupConversations: A cache of all the group windows.

    @type persons: C{dict} with keys that are a C{tuple} of (C{str},
        L{Account<interfaces.IAccount>}) and values that are
        L{Person<interfaces.IPerson>}.
    @ivar persons: A cache of all the users associated with this client.

    @type groups: C{dict} with keys that are a C{tuple} of (C{str},
        L{Account<interfaces.IAccount>}) and values that are
        L{Group<interfaces.IGroup>}
    @ivar groups: A cache of all the groups associated with this client.

    @type onlineClients: C{list} of L{Client<interfaces.IClient>}
    @ivar onlineClients: A list of message sources currently online.

    @type contactsList: L{ContactsList}
    @ivar contactsList: A contacts list.
    """
    def __init__(self):
        """
        @type conversations: C{dict} of L{Conversation}.
        @param conversations: A cache of all the direct windows.

        @type groupConversations: C{dict} of L{GroupConversation}.
        @param groupConversations: A cache of all the group windows.

        @type persons: C{dict} with keys that are a C{tuple} of (C{str},
            L{Account<interfaces.IAccount>}) and values that are
            L{Person<interfaces.IPerson>}.
        @param persons: A cache of all the users associated with this client.

        @type groups: C{dict} with keys that are a C{tuple} of (C{str},
            L{Account<interfaces.IAccount>}) and values that are
            L{Group<interfaces.IGroup>}
        @param groups: A cache of all the groups associated with this client.

        @type onlineClients: C{list} of L{Client<interfaces.IClient>}
        @param onlineClients: A list of message sources currently online.

        @type contactsList: L{ContactsList}
        @param contactsList: A contacts list.
        """
        self.conversations = {}
        self.groupConversations = {}
        self.persons = {}
        self.groups = {}
        self.onlineClients = []
        self.contactsList = ContactsList(self)


    def registerAccountClient(self, client):
        """
        Notifies user that an account has been signed on to.

        @type client: L{Client<interfaces.IClient>}
        @param client: The client account for the person who has just signed on.

        @rtype client: L{Client<interfaces.IClient>}
        @returns: The client, so that it may be used in a callback chain.
        """
        self.onlineClients.append(client)
        self.contactsList.registerAccountClient(client)
        return client


    def unregisterAccountClient(self, client):
        """
        Notifies user that an account has been signed off or disconnected.

        @type client: L{Client<interfaces.IClient>}
        @param client: The client account for the person who has just signed
            off.
        """
        self.onlineClients.remove(client)
        self.contactsList.unregisterAccountClient(client)


    def getContactsList(self):
        """
        Gets the contacts list associated with this chat window.

        @rtype: L{ContactsList}
        @returns: The contacts list associated with this chat window.
        """
        return self.contactsList


    def getConversation(self, person, Class=Conversation, stayHidden=False):
        """
        For the given person object, returns the conversation window
        or creates and returns a new conversation window if one does not exist.

        @type person: L{Person<interfaces.IPerson>}
        @param person: The person whose conversation window we want to get.

        @type Class: L{Conversation<interfaces.IConversation>} class
        @param: The kind of conversation window we want. If the conversation
            window for this person didn't already exist, create one of this type.

        @type stayHidden: C{bool}
        @param stayHidden: Whether or not the conversation window should stay
            hidden.

        @rtype: L{Conversation<interfaces.IConversation>}
        @returns The conversation window.
        """
        conv = self.conversations.get(person)
        if not conv:
            conv = Class(person, self)
            self.conversations[person] = conv
        if stayHidden:
            conv.hide()
        else:
            conv.show()
        return conv


    def getGroupConversation(self, group, Class=GroupConversation,
                             stayHidden=False):
        """
        For the given group object, returns the group conversation window or
        creates and returns a new group conversation window if it doesn't exist.

        @type group: L{Group<interfaces.IGroup>}
        @param group: The group whose conversation window we want to get.

        @type Class: L{Conversation<interfaces.IConversation>} class
        @param: The kind of conversation window we want. If the conversation
            window for this person didn't already exist, create one of this type.

        @type stayHidden: C{bool}
        @param stayHidden: Whether or not the conversation window should stay
            hidden.

        @rtype: L{GroupConversation<interfaces.IGroupConversation>}
        @returns The group conversation window.
        """
        conv = self.groupConversations.get(group)
        if not conv:
            conv = Class(group, self)
            self.groupConversations[group] = conv
        if stayHidden:
            conv.hide()
        else:
            conv.show()
        return conv


    def getPerson(self, name, client):
        """
        For the given name and account client, returns an instance of an
        L{Group<interfaces.IPerson>} implementer or creates and returns a new
        instance of an L{Group<interfaces.IPerson>} implementer.

        @type name: C{str}
        @param name: The name of the person of interest.

        @type client: L{Client<interfaces.IClient>}
        @param client: The client account of interest.

        @rtype: L{Person<interfaces.IPerson>}
        @returns: The person with that C{name}.
        """
        account = client.account
        p = self.persons.get((name, account))
        if not p:
            p = account.getPerson(name)
            self.persons[name, account] = p
        return p


    def getGroup(self, name, client):
        """
        For the given name and account client, returns an instance of an
        L{Group<interfaces.IGroup>} implementer or creates and returns a new
        instance of an L{Group<interfaces.IGroup>} implementer.

        @type name: C{str}
        @param name: The name of the group of interest.

        @type client: L{Client<interfaces.IClient>}
        @param client: The client account of interest.

        @rtype: L{Group<interfaces.IGroup>}
        @returns: The group with that C{name}.
        """
        # I accept 'client' instead of 'account' in my signature for
        # backwards compatibility.  (Groups changed to be Account-oriented
        # in CVS revision 1.8.)
        account = client.account
        g = self.groups.get((name, account))
        if not g:
            g = account.getGroup(name)
            self.groups[name, account] = g
        return g


    def contactChangedNick(self, person, newnick):
        """
        For the given C{person}, change the C{person}'s C{name} to C{newnick}
        and tell the contact list and any conversation windows with that
        C{person} to change as well.

        @type person: L{Person<interfaces.IPerson>}
        @param person: The person whose nickname will get changed.

        @type newnick: C{str}
        @param newnick: The new C{name} C{person} will take.
        """
        oldnick = person.name
        if self.persons.has_key((oldnick, person.account)):
            conv = self.conversations.get(person)
            if conv:
                conv.contactChangedNick(person, newnick)
            self.contactsList.contactChangedNick(person, newnick)
            del self.persons[oldnick, person.account]
            person.name = newnick
            self.persons[person.name, person.account] = person
