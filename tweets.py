
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, validator
from typing import Optional
import re
from notifications import create_notification
from websocket import manager
import asyncio

from database import get_db
from models import Tweet, Like, Retweet, Bookmark, Hashtag, TweetHashtag, User, Follow
from auth import get_current_user

router = APIRouter(prefix="/tweets", tags=["Tweets"])


# --- Schemas ----====---------------

class TweetCreate(BaseModel):
    body: str
    reply_to_id: Optional[int] = None

    @validator("reply_to_id", pre=True)
    def reject_zero(cls,v):
        if v == 0:
            return None
        return v

    


# --- Hashtag extractor ----====-----

def extract_hashtags(text: str) -> list[str]:
    return list(set(tag.lower() for tag in re.findall(r"#(\w+)", text)))


def attach_hashtags(tweet: Tweet, tags: list[str], db: Session):
    for tag in tags:
        hashtag = db.query(Hashtag).filter(Hashtag.tag == tag).first()
        if not hashtag:
            hashtag = Hashtag(tag=tag)
            db.add(hashtag)
            db.flush()   # get hashtag.id without full commit
        db.add(TweetHashtag(tweet_id=tweet.id, hashtag_id=hashtag.id))


# --- Tweet serializer ----====------

def serialize_tweet(tweet: Tweet, db: Session, current_user_id: int = None) -> dict:
    like_count    = db.query(Like).filter(Like.tweet_id == tweet.id).count()
    retweet_count = db.query(Retweet).filter(Retweet.tweet_id == tweet.id).count()
    reply_count   = db.query(Tweet).filter(Tweet.reply_to_id == tweet.id).count()

    liked     = False
    retweeted = False
    bookmarked = False

    if current_user_id:
        liked = db.query(Like).filter(
            Like.tweet_id == tweet.id,
            Like.user_id  == current_user_id
        ).first() is not None

        retweeted = db.query(Retweet).filter(
            Retweet.tweet_id == tweet.id,
            Retweet.user_id  == current_user_id
        ).first() is not None

        bookmarked = db.query(Bookmark).filter(
            Bookmark.tweet_id == tweet.id,
            Bookmark.user_id  == current_user_id
        ).first() is not None

    tags = [th.hashtag.tag for th in tweet.hashtags]

    return {
        "id":           tweet.id,
        "body":         tweet.body,
        "reply_to_id":  tweet.reply_to_id,
        "created_at":   tweet.created_at.isoformat(),
        "author": {
            "id":           tweet.author.id,
            "username":     tweet.author.username,
            "display_name": tweet.author.display_name,
            "avatar_url":   tweet.author.avatar_url,
        },
        "like_count":    like_count,
        "retweet_count": retweet_count,
        "reply_count":   reply_count,
        "liked":         liked,
        "retweeted":     retweeted,
        "bookmarked":    bookmarked,
        "hashtags":      tags,
    }


# --- Post a tweet ----====----------

@router.post("/", status_code=201)
def post_tweet(
    data: TweetCreate,
    db:   Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if len(data.body.strip()) == 0:
        raise HTTPException(status_code=400, detail="Tweet cannot be empty")
    if len(data.body) > 280:
        raise HTTPException(status_code=400, detail="Tweet exceeds 280 characters")

    # If it's a reply, confirm parent exists
    if data.reply_to_id:
        parent = db.query(Tweet).filter(Tweet.id == data.reply_to_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent tweet not found")

    tweet = Tweet(
        author_id   = current_user.id,
        body        = data.body.strip(),
        reply_to_id = data.reply_to_id,
    )
    db.add(tweet)
    db.commit()
    db.refresh(tweet)

    # Attach hashtags
    tags = extract_hashtags(tweet.body)
    if tags:
        attach_hashtags(tweet, tags, db)
        db.commit()
        asyncio.run(manager.broadcast({
            "type": "new_tweet",
            "tweet_id": tweet.id,
            "author": current_user.username ,
        }))
        db.refresh(tweet)

    return serialize_tweet(tweet, db, current_user.id)


# --- Get single tweet ----====------

@router.get("/{tweet_id}")
def get_tweet(
    tweet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")
    return serialize_tweet(tweet, db, current_user.id)


# --- Delete a tweet ----====--------

@router.delete("/{tweet_id}", status_code=204)
def delete_tweet(
    tweet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")
    if tweet.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your tweet")
    db.delete(tweet)
    db.commit()


# --- Home feed ----====-------------

@router.get("/")
def get_feed(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # IDs of people current user follows
    following_ids = db.query(Follow.following_id).filter(
        Follow.follower_id == current_user.id
    ).subquery()

    tweets = (
        db.query(Tweet)
        .filter(
            Tweet.reply_to_id == None,   # top-level tweets only
            Tweet.author_id.in_(following_ids)
        )
        .order_by(Tweet.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [serialize_tweet(t, db, current_user.id) for t in tweets]


# --- Explore feed (everyone) ---------------------

@router.get("/explore/all")
def explore(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tweets = (
        db.query(Tweet)
        .filter(Tweet.reply_to_id == None)
        .order_by(Tweet.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [serialize_tweet(t, db, current_user.id) for t in tweets]


# --- Get replies for a tweet ---------------------

@router.get("/{tweet_id}/replies")
def get_replies(
    tweet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    replies = (
        db.query(Tweet)
        .filter(Tweet.reply_to_id == tweet_id)
        .order_by(Tweet.created_at.asc())
        .all()
    )
    return [serialize_tweet(r, db, current_user.id) for r in replies]


# --- Like / Unlike ----====---------

@router.post("/{tweet_id}/like")
def toggle_like(
    tweet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    existing = db.query(Like).filter(
        Like.tweet_id == tweet_id,
        Like.user_id  == current_user.id
    ).first()

    if existing:
        db.delete(existing)
        liked = False
    else:
        db.add(Like(user_id=current_user.id, tweet_id=tweet_id))
        liked = True

    db.commit()
    if liked:
        create_notification(db,tweet.author_id,current_user.id,"like",tweet_id)
        asyncio.run(manager.send_to_user(tweet.author_id, {
            "type": "notification",
            "kind": "like",
            "actor": current_user.username,
            "tweet_id": tweet_id
        }))
    count = db.query(Like).filter(Like.tweet_id == tweet_id).count()
    return {"liked": liked, "like_count": count}


# --- Retweet / Undo retweet ----====

@router.post("/{tweet_id}/retweet")
def toggle_retweet(
    tweet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")
    if tweet.author_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot retweet your own tweet")

    existing = db.query(Retweet).filter(
        Retweet.tweet_id == tweet_id,
        Retweet.user_id  == current_user.id
    ).first()

    if existing:
        db.delete(existing)
        retweeted = False
    else:
        db.add(Retweet(user_id=current_user.id, tweet_id=tweet_id))
        retweeted = True

    db.commit()
    if retweeted:
        create_notification(db,tweet.author_id,current_user.id,"retweet",tweet_id)
        asyncio.run(manager.send_to_user(tweet.author_id, {
            "type": "notification",
            "kind": "retweet",
            "actor": current_user.username,
            "tweet_id": tweet_id
        }))
    count = db.query(Retweet).filter(Retweet.tweet_id == tweet_id).count()
    return {"retweeted": retweeted, "retweet_count": count}


# --- Bookmark / Unbookmark ----====-

@router.post("/{tweet_id}/bookmark")
def toggle_bookmark(
    tweet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    existing = db.query(Bookmark).filter(
        Bookmark.tweet_id == tweet_id,
        Bookmark.user_id  == current_user.id
    ).first()

    if existing:
        db.delete(existing)
        bookmarked = False
    else:
        db.add(Bookmark(user_id=current_user.id, tweet_id=tweet_id))
        bookmarked = True

    db.commit()
    return {"bookmarked": bookmarked}


# --- My bookmarks ----====----------

@router.get("/me/bookmarks")
def my_bookmarks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bookmarks = (
        db.query(Bookmark)
        .filter(Bookmark.user_id == current_user.id)
        .order_by(Bookmark.created_at.desc())
        .all()
    )
    return [serialize_tweet(b.tweet, db, current_user.id) for b in bookmarks]


# --- Trending hashtags ----====-----

@router.get("/hashtags/trending")
def trending(db: Session = Depends(get_db)):
    results = (
        db.query(Hashtag.tag, func.count(TweetHashtag.id).label("count"))
        .join(TweetHashtag, TweetHashtag.hashtag_id == Hashtag.id)
        .group_by(Hashtag.tag)
        .order_by(func.count(TweetHashtag.id).desc())
        .limit(10)
        .all()
    )
    return [{"tag": r.tag, "count": r.count} for r in results]


# --- Search tweets ----====---------

@router.get("/search/query")
def search(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tweets = (
        db.query(Tweet)
        .filter(Tweet.body.ilike(f"%{q}%"))
        .order_by(Tweet.created_at.desc())
        .limit(20)
        .all()
    )
    return [serialize_tweet(t, db, current_user.id) for t in tweets]