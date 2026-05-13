
from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from sqlalchemy.orm import relationship, backref as sa_backref
# --- User ----====------------------

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(50),  unique=True, nullable=False, index=True)
    email           = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name    = Column(String(100), nullable=True)
    bio             = Column(Text,        nullable=True)
    avatar_url      = Column(String(500), nullable=True)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tweets        = relationship("Tweet",        back_populates="author",     cascade="all, delete-orphan")
    likes         = relationship("Like",         back_populates="user",       cascade="all, delete-orphan")
    retweets      = relationship("Retweet",      back_populates="user",       cascade="all, delete-orphan")
    bookmarks     = relationship("Bookmark",     back_populates="user",       cascade="all, delete-orphan")
    notifications = relationship("Notification",foreign_keys="Notification.recipient_id", back_populates="recipient",  cascade="all, delete-orphan")

    following = relationship("Follow", foreign_keys="Follow.follower_id",
                             back_populates="follower", cascade="all, delete-orphan")
    followers = relationship("Follow", foreign_keys="Follow.following_id",
                             back_populates="following")


# --- Tweet ----====-----------------

class Tweet(Base):
    __tablename__ = "tweets"

    id           = Column(Integer, primary_key=True, index=True)
    author_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body         = Column(String(280), nullable=False)   # Twitter's 280 char limit
    reply_to_id  = Column(Integer, ForeignKey("tweets.id", ondelete="CASCADE"), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    author    = relationship("User",    back_populates="tweets")
    likes     = relationship("Like",    back_populates="tweet",   cascade="all, delete-orphan")
    retweets  = relationship("Retweet", back_populates="tweet",   cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark",back_populates="tweet",   cascade="all, delete-orphan")
    hashtags  = relationship("TweetHashtag", back_populates="tweet", cascade="all, delete-orphan")

    # Self-referential — a reply points to its parent tweet
    

    replies = relationship(
    "Tweet",
    foreign_keys=[reply_to_id],
    backref=sa_backref("parent", remote_side="Tweet.id"),
    cascade="all, delete-orphan")



# --- Like ----====------------------

class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "tweet_id", name="unique_like"),)

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id",   ondelete="CASCADE"), nullable=False)
    tweet_id   = Column(Integer, ForeignKey("tweets.id",  ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user  = relationship("User",  back_populates="likes")
    tweet = relationship("Tweet", back_populates="likes")


# --- Retweet ----====---------------

class Retweet(Base):
    __tablename__ = "retweets"
    __table_args__ = (UniqueConstraint("user_id", "tweet_id", name="unique_retweet"),)

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id",  ondelete="CASCADE"), nullable=False)
    tweet_id   = Column(Integer, ForeignKey("tweets.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user  = relationship("User",  back_populates="retweets")
    tweet = relationship("Tweet", back_populates="retweets")


# --- Follow ----====----------------

class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "following_id", name="unique_follow"),)

    id           = Column(Integer, primary_key=True, index=True)
    follower_id  = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    following_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    follower  = relationship("User", foreign_keys=[follower_id],  back_populates="following")
    following = relationship("User", foreign_keys=[following_id], back_populates="followers")


# --- Hashtag ----====---------------

class Hashtag(Base):
    __tablename__ = "hashtags"

    id         = Column(Integer, primary_key=True, index=True)
    tag        = Column(String(100), unique=True, nullable=False, index=True)

    tweets     = relationship("TweetHashtag", back_populates="hashtag",
                              cascade="all, delete-orphan")


class TweetHashtag(Base):
    __tablename__ = "tweet_hashtags"

    id         = Column(Integer, primary_key=True, index=True)
    tweet_id   = Column(Integer, ForeignKey("tweets.id",   ondelete="CASCADE"), nullable=False)
    hashtag_id = Column(Integer, ForeignKey("hashtags.id", ondelete="CASCADE"), nullable=False)

    tweet   = relationship("Tweet",   back_populates="hashtags")
    hashtag = relationship("Hashtag", back_populates="tweets")


# --- Bookmark ----====--------------

class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "tweet_id", name="unique_bookmark"),)

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id",  ondelete="CASCADE"), nullable=False)
    tweet_id   = Column(Integer, ForeignKey("tweets.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user  = relationship("User",  back_populates="bookmarks")
    tweet = relationship("Tweet", back_populates="bookmarks")


# --- Notification ----====----------

class Notification(Base):
    __tablename__ = "notifications"

    id           = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    actor_id     = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    kind         = Column(String(50), nullable=False)  # "like" "retweet" "follow" "reply"
    tweet_id     = Column(Integer, ForeignKey("tweets.id", ondelete="CASCADE"), nullable=True)
    is_read      = Column(Boolean, default=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="notifications")
    actor     = relationship("User", foreign_keys=[actor_id], overlaps="Notification")


