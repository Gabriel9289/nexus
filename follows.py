from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from notifications import create_notification
from websocket import manager
import asyncio

from database import get_db
from models import User, Follow, Tweet, Like, Retweet
from auth import get_current_user
from tweets import serialize_tweet

router = APIRouter(tags=["Follows & Profiles"])


# --- Profile serializer ----====----

def serialize_user(user: User, db: Session, current_user_id: int = None) -> dict:
    follower_count  = db.query(Follow).filter(Follow.following_id == user.id).count()
    following_count = db.query(Follow).filter(Follow.follower_id  == user.id).count()
    tweet_count     = db.query(Tweet).filter(
        Tweet.author_id   == user.id,
        Tweet.reply_to_id == None
    ).count()

    is_following = False
    if current_user_id and current_user_id != user.id:
        is_following = db.query(Follow).filter(
            Follow.follower_id  == current_user_id,
            Follow.following_id == user.id
        ).first() is not None

    return {
        "id":               user.id,
        "username":         user.username,
        "display_name":     user.display_name,
        "bio":              user.bio,
        "avatar_url":       user.avatar_url,
        "follower_count":   follower_count,
        "following_count":  following_count,
        "tweet_count":      tweet_count,
        "is_following":     is_following,
        "joined":           user.created_at.isoformat(),
    }


# --- Get profile ----====-----------

@router.get("/users/{username}")
def get_profile(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_user(user, db, current_user.id)


# --- Get user tweets ----====-------

@router.get("/users/{username}/tweets")
def get_user_tweets(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tweets = (
        db.query(Tweet)
        .filter(
            Tweet.author_id   == user.id,
            Tweet.reply_to_id == None
        )
        .order_by(Tweet.created_at.desc())
        .all()
    )
    return [serialize_tweet(t, db, current_user.id) for t in tweets]


# --- Get user replies ----====------

@router.get("/users/{username}/replies")
def get_user_replies(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    replies = (
        db.query(Tweet)
        .filter(
            Tweet.author_id   == user.id,
            Tweet.reply_to_id != None
        )
        .order_by(Tweet.created_at.desc())
        .all()
    )
    return [serialize_tweet(r, db, current_user.id) for r in replies]


# --- Get user likes ----====--------

@router.get("/users/{username}/likes")
def get_user_likes(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    liked = (
        db.query(Like)
        .filter(Like.user_id == user.id)
        .order_by(Like.created_at.desc())
        .all()
    )
    return [serialize_tweet(l.tweet, db, current_user.id) for l in liked]


# --- Follow / Unfollow ----====-----

@router.post("/users/{username}/follow")
def toggle_follow(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")

    existing = db.query(Follow).filter(
        Follow.follower_id  == current_user.id,
        Follow.following_id == target.id
    ).first()

    if existing:
        db.delete(existing)
        following = False
    else:
        db.add(Follow(
            follower_id  = current_user.id,
            following_id = target.id
        ))
        following = True

    db.commit()
    if following:
        create_notification(db,target.id,current_user.id,"follow")
        asyncio.run(manager.send_to_user(target.id, {
            "type": "notification",
            "kind": "follow",
            "actor": current_user.username,
        }))

    follower_count = db.query(Follow).filter(
        Follow.following_id == target.id
    ).count()

    return {
        "following":       following,
        "follower_count":  follower_count,
        "message": f"Following {username}" if following else f"Unfollowed {username}"
    }


# --- Get followers list ----====----

@router.get("/users/{username}/followers")
def get_followers(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    follows = db.query(Follow).filter(Follow.following_id == user.id).all()
    return [serialize_user(f.follower, db, current_user.id) for f in follows]


# --- Get following list ----====----

@router.get("/users/{username}/following")
def get_following(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    follows = db.query(Follow).filter(Follow.follower_id == user.id).all()
    return [serialize_user(f.following, db, current_user.id) for f in follows]


# --- Who to follow (suggestions) ----------------

@router.get("/suggestions/who-to-follow")
def who_to_follow(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get IDs already followed
    already_following = db.query(Follow.following_id).filter(
        Follow.follower_id == current_user.id
    ).subquery()

    suggestions = (
        db.query(User)
        .filter(
            User.id != current_user.id,
            User.id.not_in(already_following)
        )
        .order_by(User.created_at.desc())
        .limit(5)
        .all()
    )
    return [serialize_user(u, db, current_user.id) for u in suggestions]



