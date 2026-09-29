# AI-Powered Nearby Business & Service Discovery Chatbot

An AI-powered chatbot that helps users find nearby businesses and services using natural language. Built with Django, Groq API (Llama 3.3 70B), and a simple HTML/JS frontend.

## Features

- **Natural Language Understanding** — Ask in plain English: "Find hotels near me", "Show restaurants in Gandhipuram"
- **AI-Powered Search** — Groq LLM extracts category, location, and radius from your query
- **Location-Based Results** — Browser geolocation or mock Coimbatore location
- **Search Radius** — Supports 1 km, 5 km, and 10 km radius
- **Business Cards** — Rich result cards with name, rating, distance, phone, area
- **Voice Input** — Click the microphone and speak your query (Chrome only)
- **550+ Businesses** — Across 11 categories in Coimbatore

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5 + Django REST Framework |
| AI/NLU | Groq API — Llama 3.3 70B Versatile |
| Database | SQLite |
| Frontend | HTML + CSS + Vanilla JS |
| Location | Haversine formula for distance calc |

## Project Structure

```
Cybexcel/
├── backend/
│   ├── config/              # Django settings, URLs, WSGI
│   ├── chatbot/             # Main app
│   │   ├── models.py        # Business model
│   │   ├── services.py      # Groq NLU extraction
│   │   ├── utils.py         # Haversine distance, search logic
│   │   ├── views.py         # API views
│   │   ├── urls.py          # URL routing
│   │   ├── admin.py         # Admin config
│   │   ├── templates/       # Chat UI template
│   │   ├── static/          # CSS + JS
│   │   └── management/      # Data import command
│   ├── manage.py
│   ├── requirements.txt
│   └── .env                 # API keys
├── data/
│   └── db.sqlite3           # SQLite database
└── README.md
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `backend/.env` and add your Groq API key:

```
GROQ_API_KEY=your-api-key-here
GROQ_MODEL=llama-3.3-70b-versatile
DEBUG=True
SECRET_KEY=your-secret-key
```

### 3. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Import Business Data

```bash
python manage.py import_data
```

This imports all 550 records from `DATA-FILEE.xlsx` into SQLite.

### 5. Run the Server

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000 in your browser.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/` | POST | Process chat message, return businesses |
| `/api/search/` | GET | Direct search with query params |
| `/api/businesses/<id>/` | GET | Get business details |
| `/api/categories/` | GET | List all categories |
| `/api/areas/` | GET | List known areas |

### API Examples

**Chat endpoint:**
```bash
curl -X POST http://127.0.0.1:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"query": "Find hotels near me", "latitude": 11.0168, "longitude": 76.9558}'
```

**Search endpoint:**
```bash
curl "http://127.0.0.1:8000/api/search/?category=Hotel&area=Gandhipuram&radius=5"
```

## How It Works

1. **User asks**: "Find hotels near me"
2. **Groq LLM extracts**: `{category: "Hotel", location: "current_location", radius_km: 5}`
3. **Backend searches**: SQLite database filtered by category + Haversine distance
4. **Results returned**: Business cards with name, rating, distance, phone
5. **Frontend displays**: Chat message + rich business cards

## Test Queries

Try these example queries:
- "Hotels near me"
- "I need a dentist nearby"
- "Show textile shops in Coimbatore"
- "Find a car service center within 5 km"
- "Show restaurants in Gandhipuram"
- "Find gyms near Peelamedu"
- "Electronics stores in RS Puram"
- "Find a hospital within 10 km"
