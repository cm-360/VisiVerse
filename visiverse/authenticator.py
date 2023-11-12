from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from visiverse.database import User


class Authenticator():

    def __init__(self, db):
        self.db = db
        self.hasher = PasswordHasher()

    async def register_user(self, username, password):
        async with self.db.async_session() as session, session.begin():
            try:
                password_hash = self.hasher.hash(password)
                user = User(
                    username=username,
                    password_hash=password_hash,
                )
                await self.db.insert_object(session, user)
            except:
                raise ValueError("Duplicate user")

    async def authenticate(self, username, password):
        async with self.db.async_session() as session:
            try:
                user = await self.db.get_user(session, username)
                self.hasher.verify(user.password_hash, password)
            except:
                raise AuthenticationError("Invalid credentials")
            # Update password hash if needed
            if self.hasher.check_needs_rehash(user.password_hash):
                async with session.begin():
                    new_hash = self.hasher.hash(password)
                    await self.db.update_user(session, user.username, password_hash=new_hash)
        return user


class AuthenticationError(Exception):

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
