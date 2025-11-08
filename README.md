# Game Checklist Progresser

A Python-based web application for creating, sharing, and tracking game checklists within a community.

## Features

- **User Authentication**: Secure registration and login system
- **Create Checklists**: Build comprehensive checklists for your favorite games
- **Share with Community**: Make your checklists public for others to discover
- **Copy Checklists**: Fork community checklists to your own account
- **Track Progress**: Monitor your completion percentage for each checklist
- **Browse & Search**: Find checklists by game name
- **Personal Dashboard**: View all your created checklists and progress tracking
- **Category & Reward System**: Organize items by category and track rewards
  - Assign multiple rewards to checklist items
  - Filter items by category or reward type
  - Visual badges for easy identification

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: SQLAlchemy with SQLite (easily upgradable to PostgreSQL/MySQL)
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF with WTForms
- **Frontend**: HTML5, CSS3 (responsive design)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/kelvinzhu2000/game-checklist-progresser.git
cd game-checklist-progresser
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set environment variables (optional):
```bash
export SECRET_KEY='your-secret-key-here'
export DATABASE_URL='sqlite:///game_checklist.db'
```

5. **For existing databases** (upgrading from an older version):
```bash
# Run migrations to update your database schema
python add_reward_tables_migration.py
```
   This will:
   - Add the reward system tables
   - Clean up any legacy schema issues
   - Preserve all your existing data

6. Run the application:
```bash
python run.py
```

7. Open your browser and navigate to:
```
http://localhost:5000
```

> **Note**: If you encounter errors about `game_name` or database schema, see the [MIGRATION.md](MIGRATION.md) guide for detailed migration instructions.

## Usage

### Creating a Checklist

1. Register for an account or log in
2. Click "Create" in the navigation menu
3. Fill in the checklist details:
   - Title: Name of your checklist
   - Game Name: Which game is this for
   - Description: Optional details about the checklist
   - Make Public: Allow others to see and copy
4. Add items to your checklist

### Tracking Progress

1. Browse public checklists or search by game name
2. Click "Copy to My Checklists" on any public checklist
3. Check off items as you complete them
4. Monitor your progress percentage

### Managing Your Checklists

- View all your created checklists in "My Checklists"
- See how many users have copied your checklists
- Track your progress on copied checklists

## Database Schema

### User
- id, username, email, password_hash, created_at

### Checklist
- id, title, game_name, description, creator_id, is_public, created_at, updated_at

### ChecklistItem
- id, checklist_id, title, description, order, created_at

### UserChecklist
- id, user_id, checklist_id, created_at

### UserProgress
- id, user_checklist_id, item_id, completed, completed_at

## Security

- Passwords are hashed using Werkzeug's security functions
- CSRF protection enabled via Flask-WTF
- Login required for sensitive operations
- Private checklists are protected from unauthorized access

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Project Structure

```
game-checklist-progresser/
├── app/
│   ├── __init__.py          # Application factory
│   ├── models.py            # Database models
│   ├── routes.py            # URL routes and views
│   ├── forms.py             # WTForms definitions
│   ├── static/
│   │   └── css/
│   │       └── style.css    # Stylesheet
│   └── templates/           # HTML templates
├── tests/                   # Test files
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.
