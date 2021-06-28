"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User, Likes, Follows
from bs4 import BeautifulSoup

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        #Create the primary test user
        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        self.testuser_id = 8989
        self.testuser.id = self.testuser_id

        #Create four additional dummy users which will get used for testing purposes
        self.u1 = User.signup("abc", "test1@test.com", "password", None)
        self.u1_id = 778
        self.u1.id = self.u1_id
        self.u2 = User.signup("efg", "test2@test.com", "password", None)
        self.u2_id = 884
        self.u2.id = self.u2_id
        self.u3 = User.signup("hij", "test3@test.com", "password", None)
        self.u4 = User.signup("testing", "test4@test.com", "password", None)

        db.session.commit()

    def tearDown(self):
        resp = super().tearDown()
        db.session.rollback()
        return resp

    def test_users_index(self):
        """Test the '/users' route"""
        with self.client as c:
            resp = c.get("/users")

            #Assert that the primary test user, and the four dummy users all appear on the roster of users
            self.assertIn("@testuser", str(resp.data))
            self.assertIn("@abc", str(resp.data))
            self.assertIn("@efg", str(resp.data))
            self.assertIn("@hij", str(resp.data))
            self.assertIn("@testing", str(resp.data))

    def test_users_search(self):
        """Test the '/users' route when it's provided a search query"""
        with self.client as c:
            #use the search string 'test'
            resp = c.get("/users?q=test")

            #assert that the response includes '@testuser' and '@testing'
            self.assertIn("@testuser", str(resp.data))
            self.assertIn("@testing", str(resp.data))            

            #assert the response does not include the other dummy users whose names don't include the string 'test'
            self.assertNotIn("@abc", str(resp.data))
            self.assertNotIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))

    def test_user_show(self):
        """Test the '/users/<int:user_id>' route"""
        with self.client as c:
            #Use the id of testuser
            resp = c.get(f"/users/{self.testuser_id}")
            #Assert that a page is returned successfully
            self.assertEqual(resp.status_code, 200)
            #Assert that 'testuser' is in the returned data
            self.assertIn("@testuser", str(resp.data))

    def setup_likes(self):
        """Additional set-up for testing likes"""
        #Create three dummy messages, two from testuser, one from dummy user u1
        m1 = Message(text="trending warble", user_id=self.testuser_id)
        m2 = Message(text="Eating some lunch", user_id=self.testuser_id)
        m3 = Message(id=9876, text="likable warble", user_id=self.u1_id)
        db.session.add_all([m1, m2, m3])
        db.session.commit()

        l1 = Likes(user_id=self.testuser_id, message_id=9876)

        db.session.add(l1)
        db.session.commit()

    def test_user_show_with_likes(self):
        """Test the 'users/<int:user_id>' route for the functionality of 'likes'"""
        self.setup_likes()

        with self.client as c:
            resp = c.get(f"/users/{self.testuser_id}")

            #Assert page loaded properly
            self.assertEqual(resp.status_code, 200)

            #Assert that it is the user page belonging to testuser
            self.assertIn("@testuser", str(resp.data))
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)

            # test for a count of 2 messages
            self.assertIn("2", found[0].text)

            # Test for a count of 0 followers
            self.assertIn("0", found[1].text)

            # Test for a count of 0 following
            self.assertIn("0", found[2].text)

            # Test for a count of 1 like
            self.assertIn("1", found[3].text)

    def test_add_like(self):
        """Test whether a like is added when the thumbs-up icon is clicked"""
        #create dummy message from user u1
        m = Message(id=1984, text="The earth is round", user_id=self.u1_id)
        db.session.add(m)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            #have testuser 'like' the message from u1
            resp = c.post("/messages/1984/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            #assert that the message is in testuser's likes
            likes = Likes.query.filter(Likes.message_id==1984).all()
            self.assertEqual(len(likes), 1)
            self.assertEqual(likes[0].user_id, self.testuser_id)

    def test_remove_like(self):
        """Test whether a like is removed when the thumbs-up icon is clicked"""
        self.setup_likes()

        m = Message.query.filter(Message.text=="likable warble").one()
        self.assertIsNotNone(m)
        self.assertNotEqual(m.user_id, self.testuser_id)

        l = Likes.query.filter(
            Likes.user_id==self.testuser_id and Likes.message_id==m.id
        ).one()

        # Now we are sure that testuser likes the message "likable warble"
        self.assertIsNotNone(l)

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            #click the thumbs-up icon once again, 'unliking' the message
            resp = c.post(f"/messages/{m.id}/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id==m.id).all()
            # the like has been deleted
            self.assertEqual(len(likes), 0)

    def test_unauthenticated_like(self):
        """Test that an unauthenticated user can't 'like' a message"""
        self.setup_likes()

        m = Message.query.filter(Message.text=="likable warble").one()
        self.assertIsNotNone(m)

        like_count = Likes.query.count()

        with self.client as c:
            #like the post as an unauthenticated user
            resp = c.post(f"/messages/{m.id}/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            self.assertIn("Access unauthorized", str(resp.data))

            # The number of likes has not changed since making the request
            self.assertEqual(like_count, Likes.query.count())

    def setup_followers(self):
        """Additional set-up for testing follows"""
        #Users u1 and u2 are being followed by testuser 
        f1 = Follows(user_being_followed_id=self.u1_id, user_following_id=self.testuser_id)
        f2 = Follows(user_being_followed_id=self.u2_id, user_following_id=self.testuser_id)
        #Testuser is being followed by user u1
        f3 = Follows(user_being_followed_id=self.testuser_id, user_following_id=self.u1_id)

        db.session.add_all([f1,f2,f3])
        db.session.commit()

    def test_user_show_with_follows(self):
        """Test route '/users/<int:user_id>"""
        self.setup_followers()

        with self.client as c:
            #view the page of testuser
            resp = c.get(f"/users/{self.testuser_id}")

            self.assertEqual(resp.status_code, 200)

            self.assertIn("@testuser", str(resp.data))
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)

            # test for a count of 0 messages
            self.assertIn("0", found[0].text)

            # Test for a count of 2 following
            self.assertIn("2", found[1].text)

            # Test for a count of 1 follower
            self.assertIn("1", found[2].text)

            # Test for a count of 0 likes
            self.assertIn("0", found[3].text)

    def test_show_following(self):
        """Test route '/users/<int:user_id>/following'"""
        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.get(f"/users/{self.testuser_id}/following")
            self.assertEqual(resp.status_code, 200)
            #testuser is following u1 (id:abc)
            self.assertIn("@abc", str(resp.data))
            #testuser is following u2 (id:efg)
            self.assertIn("@efg", str(resp.data))
            #testuser is not following test3 (id:hij)
            self.assertNotIn("@hij", str(resp.data))
            #testuser is not following test4 (id:testing)
            self.assertNotIn("@testing", str(resp.data))

    def test_show_followers(self):
        """Test route '/users/<int:user_id>/followers'"""
        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.get(f"/users/{self.testuser_id}/followers")

            #testuser is being followed by u1 (id:abc)
            self.assertIn("@abc", str(resp.data))
            #testuser is not being followed by u2 (id:efg), test3 (id:hij), test4 (id:testing)
            self.assertNotIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))
            self.assertNotIn("@testing", str(resp.data))

    def test_unauthorized_following_page_access(self):
        """Test that route '/users/<int:user_id>/following' is not accessible by unauthorized users"""
        self.setup_followers()
        with self.client as c:

            resp = c.get(f"/users/{self.testuser_id}/following", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("@abc", str(resp.data))
            self.assertIn("Access unauthorized", str(resp.data))

    def test_unauthorized_followers_page_access(self):
        """Test that route '/users/<int:user_id>/followers' is not accessible by unauthorized users"""
        self.setup_followers()
        with self.client as c:

            resp = c.get(f"/users/{self.testuser_id}/followers", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("@abc", str(resp.data))
            self.assertIn("Access unauthorized", str(resp.data))