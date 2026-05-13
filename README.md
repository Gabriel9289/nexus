# Nexus 𝕏

A full-stack Twitter/X-inspired social platform built with FastAPI and PostgreSQL.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)
![WebSockets](https://img.shields.io/badge/WebSockets-realtime-8b5cf6)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6-f7df1e?logo=javascript)

## Features

- JWT authentication — register, login, protected routes
- Tweet, reply, retweet, delete
- Like & unlike with toggle
- Bookmark tweets
- Hashtag extraction — automatic, no manual tagging
- Trending hashtags ranked by usage
- Follow / unfollow users
- Home feed — tweets from people you follow only
- Explore feed — all tweets
- Real-time feed via WebSockets — new tweets appear instantly
- Live notifications — likes, retweets, follows pushed in real time
- Notification centre with unread count badge
- Search tweets by text or hashtag
- User profiles — tweets, replies, likes tabs
- Followers & following lists with modal
- Who to follow suggestions
- Dark mode / light mode toggle

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy ORM |
| Database | PostgreSQL |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Real-time | WebSockets (FastAPI native) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Server | Uvicorn |

## Project Structure

```
nexus/
├── backend/
│   ├── main.py           # App entry point, router registration
│   ├── database.py       # SQLAlchemy engine, session, Base
│   ├── models.py         # All 9 database models
│   ├── auth.py           # Register, login, JWT, get_current_user
│   ├── tweets.py         # Tweets, likes, retweets, bookmarks, hashtags
│   ├── follows.py        # Follow/unfollow, profiles, suggestions
│   ├── notifications.py  # Notification CRUD
│   ├── websocket.py      # ConnectionManager, WS endpoint
│   ├── .env.example
│   └── requirements.txt
└── frontend/
    ├── index.html        # Home feed, explore, notifications, bookmarks
    ├── login.html        # Register + sign in
    ├── tweet.html        # Tweet detail + replies
    ├── profile.html      # User profile + followers/following
    └── static/
        ├── css/main.css
        └── js/api.js
```

## API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Login, returns JWT + user |
| GET | `/auth/me` | Current user |

### Tweets
| Method | Endpoint | Description |
|---|---|---|
| POST | `/tweets/` | Post tweet or reply |
| GET | `/tweets/` | Home feed (following only) |
| GET | `/tweets/explore/all` | Explore feed (everyone) |
| GET | `/tweets/{id}` | Single tweet |
| DELETE | `/tweets/{id}` | Delete your tweet |
| GET | `/tweets/{id}/replies` | Get replies |
| POST | `/tweets/{id}/like` | Like / unlike toggle |
| POST | `/tweets/{id}/retweet` | Retweet / undo toggle |
| POST | `/tweets/{id}/bookmark` | Bookmark / remove toggle |
| GET | `/tweets/me/bookmarks` | My bookmarks |
| GET | `/tweets/hashtags/trending` | Top 10 trending hashtags |
| GET | `/tweets/search/query?q=` | Search tweets |

### Follows & Profiles
| Method | Endpoint | Description |
|---|---|---|
| GET | `/users/{username}` | Profile with counts |
| GET | `/users/{username}/tweets` | User's tweets |
| GET | `/users/{username}/replies` | User's replies |
| GET | `/users/{username}/likes` | Tweets user liked |
| POST | `/users/{username}/follow` | Follow / unfollow toggle |
| GET | `/users/{username}/followers` | Followers list |
| GET | `/users/{username}/following` | Following list |
| GET | `/suggestions/who-to-follow` | Follow suggestions |

### Notifications
| Method | Endpoint | Description |
|---|---|---|
| GET | `/notifications/` | My notifications |
| GET | `/notifications/unread` | Unread count |
| POST | `/notifications/read` | Mark all read |
| POST | `/notifications/{id}/read` | Mark one read |

### WebSocket
| Endpoint | Description |
|---|---|
| `ws://host/ws?token=JWT` | Real-time connection |

## Getting Started

```bash
# 1. Clone
git clone https://github.com/Gabriel9289/nexus.git
cd nexus/backend

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env with your credentials

# 5. Create database
# In PostgreSQL: CREATE DATABASE nexus;

# 6. Run
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` for API docs.
Open `frontend/index.html` to use the app.

## Database Models

`User` · `Tweet` · `Like` · `Retweet` · `Follow` · `Hashtag` · `TweetHashtag` · `Bookmark` · `Notification`

## Author

**Gabriel** — Pretoria, South Africa
Self-taught backend developer · Python · FastAPI · PostgreSQL · WebSockets
[GitHub](https://github.com/Gabriel9289)