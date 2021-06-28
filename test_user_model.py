"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows

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

        ### Create two 'users', u1 and u2
        u1 = User.signup("test1", "email1@email.com", "password", None)
        uid1 = 1111
        u1.id = uid1

        u2 = User.signup("test2", "email2@email.com", "password", None)
        uid2 = 2222
        u2.id = uid2

        db.session.commit()

        ### Get their respective User objects
        u1 = User.query.get(uid1)
        u2 = User.query.get(uid2)

        ### Bind their respective objects and IDs to the self object (so they can be used in other functions)
        self.u1 = u1
        self.uid1 = uid1

        self.u2 = u2
        self.uid2 = uid2

        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res


    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    ##################################################
    # Following tests
    ##################################################

    def test_user_follows(self):
        """Test the basic elements of following"""
        #u1 is now following u2
        self.u1.following.append(self.u2)
        db.session.commit()

        #u2 should have one follower and be following no one
        self.assertEqual(len(self.u2.following), 0)
        self.assertEqual(len(self.u2.followers), 1)
        #u1 should have no followers and be following one user
        self.assertEqual(len(self.u1.followers), 0)
        self.assertEqual(len(self.u1.following), 1)

        #Check that u1 is in u2's list of followers, and that u2 is in u1's list of users being followed
        self.assertEqual(self.u2.followers[0].id, self.u1.id)
        self.assertEqual(self.u1.following[0].id, self.u2.id)

    def test_is_following(self):
        """Test the is_following method"""
        #u1 is now following u2
        self.u1.following.append(self.u2)
        db.session.commit()

        #is_following should return true for u1 following u2
        self.assertTrue(self.u1.is_following(self.u2))
        #is_following should return false for u2 following u1
        self.assertFalse(self.u2.is_following(self.u1))

    def test_is_followed_by(self):
        """Test the is_followed_by method"""
        #u1 is now following u2
        self.u1.following.append(self.u2)
        db.session.commit()

        #is_followed_by should return true for u2 being followed by u1
        self.assertTrue(self.u2.is_followed_by(self.u1))
        #is_followed_by should return false for u1 being followed by u2
        self.assertFalse(self.u1.is_followed_by(self.u2))

    ##########################################
    # Signup Tests
    ##########################################
    def test_valid_signup(self):
        """Test whether the signup method functions when provided valid credentials"""
        u_test = User.signup("testtesttest", "testtest@test.com", "password", None)
        uid = 99999
        u_test.id = uid
        db.session.commit()

        u_test = User.query.get(uid)
        #User object should exist
        self.assertIsNotNone(u_test)
        #The username and email of the User object should match those provided
        self.assertEqual(u_test.username, "testtesttest")
        self.assertEqual(u_test.email, "testtest@test.com")
        #The password should be encrypted, so it should *not* be the same as the one provided
        self.assertNotEqual(u_test.password, "password")
        # Bcrypt strings should start with $2b$
        self.assertTrue(u_test.password.startswith("$2b$"))

    def test_invalid_username_signup(self):
        """Test that signing up with an invalid username raises an error"""
        invalid = User.signup(None, "test@test.com", "password", None)
        uid = 123456789
        invalid.id = uid
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()

    def test_invalid_email_signup(self):
        """Test that signing up with an invalid email raises an error"""
        invalid = User.signup("testtest", None, "password", None)
        uid = 123789
        invalid.id = uid
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()
    
    def test_invalid_password_signup(self):
        """Test that signing up with an invalid password raises an error"""
        with self.assertRaises(ValueError) as context:
            User.signup("testtest", "email@email.com", "", None)
        
        with self.assertRaises(ValueError) as context:
            User.signup("testtest", "email@email.com", None, None)
    
    ##############################################
    # Authentication Tests
    ##############################################
    def test_valid_authentication(self):
        """Test that the authenticate method returns the correct User object when given a valid username and password"""
        u = User.authenticate(self.u1.username, "password")
        self.assertIsNotNone(u)
        self.assertEqual(u.id, self.uid1)
    
    def test_invalid_username(self):
        """Test that the authenticate method fails to return a User object when given an invalid username"""
        self.assertFalse(User.authenticate("badusername", "password"))

    def test_wrong_password(self):
        """Test that the authenticate method fails to return a User object when given an invalid password """
        self.assertFalse(User.authenticate(self.u1.username, "badpassword"))