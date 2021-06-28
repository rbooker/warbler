"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py


import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows, Likes

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        db.drop_all()
        db.create_all()

        #Create a dummy user, for testing purposes
        self.uid = 94566
        u = User.signup("testing", "testing@test.com", "password", None)
        u.id = self.uid
        db.session.commit()

        #Bind the user object to the self object, so we can use it in other functions
        self.u = User.query.get(self.uid)

        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_message_model(self):
        """Does the basic Message model work?"""
        
        #A dummy message, for testing purposes
        m = Message(
            text="a warble",
            user_id=self.uid
        )

        db.session.add(m)
        db.session.commit()

        # User should have 1 message
        self.assertEqual(len(self.u.messages), 1)
        # Text of message whould be what we entered
        self.assertEqual(self.u.messages[0].text, "a warble")

    def test_message_likes(self):
        """Does 'liking' messages work?"""

        #Two dummy messages, m1 and m2, for testing purposes
        m1 = Message(
            text="a warble",
            user_id=self.uid
        )

        m2 = Message(
            text="a very interesting warble",
            user_id=self.uid 
        )

        #Create a second dummy user to like the messages sent by the first dummy user
        u = User.signup("yetanothertest", "t@email.com", "password", None)
        uid = 888
        u.id = uid
        db.session.add_all([m1, m2, u])
        db.session.commit()

        #The second dummy user now 'likes' message m1
        u.likes.append(m1)

        db.session.commit()

        #Make sure m1 is in the second dummy user's list of liked messages
        l = Likes.query.filter(Likes.user_id == uid).all()
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0].message_id, m1.id)