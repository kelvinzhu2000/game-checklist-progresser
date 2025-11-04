# GitHub Copilot Instructions for Game Checklist Progresser

## Project Overview
This is a Flask-based web application for creating, sharing, and tracking game checklists within a community. Users can create checklists for games, share them publicly, copy others' checklists, and track their progress.

## Technology Stack
- **Backend**: Flask 3.0.0 (Python web framework)
- **Database**: SQLAlchemy 3.1.1 with SQLite (can be upgraded to PostgreSQL/MySQL)
- **Authentication**: Flask-Login 0.6.3
- **Forms**: Flask-WTF 1.2.1 with WTForms 3.1.1
- **Frontend**: HTML5, CSS3 (responsive design, templates in `app/templates/`)
- **Testing**: pytest 7.4.3

## Project Structure
```
game-checklist-progresser/
├── app/
│   ├── __init__.py          # Application factory with create_app()
│   ├── models.py            # Database models (User, Checklist, ChecklistItem, UserChecklist, UserProgress)
│   ├── routes.py            # URL routes and views (main_bp, auth_bp, checklist_bp blueprints)
│   ├── forms.py             # WTForms definitions
│   ├── static/css/          # Stylesheets
│   └── templates/           # Jinja2 HTML templates
├── tests/                   # pytest test files
├── config.py                # Configuration classes (Development, Production, Testing)
├── run.py                   # Application entry point
└── requirements.txt         # Python dependencies
```

## Development Guidelines

### Code Style
- Follow PEP 8 Python style guidelines
- Use descriptive variable and function names
- Add docstrings to functions and classes where helpful
- Keep functions focused on a single responsibility

### Database Models
The application has 5 main models with the following relationships:

1. **User**: User accounts with authentication
   - Fields: id, username, email, password_hash, created_at
   - Relationships: created_checklists, user_checklists
   - Use `set_password()` method for password hashing (pbkdf2:sha256)
   - Use `check_password()` method for password verification

2. **Checklist**: Game checklists created by users
   - Fields: id, title, game_name, description, creator_id, is_public, created_at, updated_at
   - Relationships: items (ChecklistItem), user_copies (UserChecklist), creator (User)
   - Index on: game_name, is_public

3. **ChecklistItem**: Individual items in a checklist
   - Fields: id, checklist_id, title, description, order, created_at
   - Ordered by `order` field

4. **UserChecklist**: Junction table for users who copied checklists
   - Fields: id, user_id, checklist_id, created_at
   - Relationships: progress_items (UserProgress)
   - Method: `get_progress_percentage()` - calculates completion percentage

5. **UserProgress**: Tracks completion status of checklist items
   - Fields: id, user_checklist_id, item_id, completed, completed_at
   - Relationships: user_checklist, item (ChecklistItem)

### Authentication & Security
- **ALWAYS** use Flask-Login's `@login_required` decorator for protected routes
- **NEVER** store plain-text passwords - use `generate_password_hash()` with pbkdf2:sha256
- **ALWAYS** enable CSRF protection (Flask-WTF handles this by default)
- **ALWAYS** validate user permissions before allowing checklist modifications
- Check if checklist is public or belongs to current user before displaying
- Environment variables for sensitive config: `SECRET_KEY`, `DATABASE_URL`

### Flask Blueprints
The application uses three blueprints:
- `main_bp`: Index, browse, search functionality
- `auth_bp`: Registration, login, logout (prefix: `/auth`)
- `checklist_bp`: Create, view, edit, copy checklists (prefix: `/checklist`)

### Testing
- Use pytest for all tests
- Test files should be in `tests/` directory
- Use fixtures for app, client, and database setup
- Test configuration uses in-memory SQLite: `sqlite:///:memory:`
- Disable CSRF for testing: `WTF_CSRF_ENABLED = False`
- Always test with app context: `with app.app_context():`
- Run tests with: `python -m pytest tests/ -v`

### Database Operations
- Use SQLAlchemy ORM for all database operations
- **ALWAYS** commit changes: `db.session.add(obj)` then `db.session.commit()`
- Use `db.session.flush()` when you need the ID before commit
- Handle relationships through SQLAlchemy relationships, not manual joins
- Use `lazy='dynamic'` for relationships that may return many records

### Common Patterns

#### Creating a new checklist:
```python
checklist = Checklist(
    title=form.title.data,
    game_name=form.game_name.data,
    description=form.description.data,
    creator_id=current_user.id,
    is_public=form.is_public.data
)
db.session.add(checklist)
db.session.commit()
```

#### Copying a checklist to user's account:
```python
user_checklist = UserChecklist(
    user_id=current_user.id,
    checklist_id=checklist.id
)
db.session.add(user_checklist)
# Also create UserProgress entries for each item
```

#### Calculating progress:
```python
user_checklist.get_progress_percentage()  # Returns 0-100
```

### Configuration
- Development: Uses `config.DevelopmentConfig` with DEBUG=True
- Production: Uses `config.ProductionConfig` with DEBUG=False
- Testing: Uses `config.TestingConfig` with in-memory database
- Access via: `app.config['KEY']`

### Running the Application
- Entry point: `python run.py`
- Default port: 5000
- Debug mode: Set environment variable `FLASK_DEBUG=true`
- Database: SQLite file `game_checklist.db` (auto-created)

### Key Features to Preserve
- User registration and authentication
- Public/private checklist visibility
- Checklist copying functionality
- Progress tracking with percentage calculation
- Search and browse by game name
- Responsive design

### Common Issues to Avoid
- Don't use deprecated `datetime.utcnow()` - use `datetime.now(datetime.UTC)` instead
- Don't use `Query.get()` - use `Session.get()` instead
- Ensure proper cascade deletes are configured in relationships
- Always use app context for database operations outside request handlers
- Don't expose password_hash in API responses or templates

### When Making Changes
1. Consider impact on existing database schema
2. Update tests to cover new functionality
3. Maintain backward compatibility when possible
4. Keep security best practices in mind
5. Test authentication and authorization flows
6. Verify CSRF protection is maintained
