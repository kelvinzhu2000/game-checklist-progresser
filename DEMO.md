# Game Checklist Progresser - Demo Guide

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   python run.py
   ```

3. **Open in Browser**
   Navigate to: http://localhost:5000

## Demo Walkthrough

### 1. Register a New User
- Click "Register" in the navigation
- Fill in username, email, and password
- Submit the form
- You'll be redirected to login

### 2. Login
- Enter your username and password
- Click "Login"
- You're now logged in and can see "My Checklists" and "Create" options

### 3. Create a Checklist
- Click "Create" in the navigation
- Fill in the form:
  - **Title**: "Elden Ring 100% Completion"
  - **Game Name**: "Elden Ring"
  - **Description**: "Complete all bosses, items, and achievements"
  - **Make Public**: Check this box to share with community
- Click "Create Checklist"

### 4. Add Items to Your Checklist
- You'll be redirected to your new checklist
- Click "Add Item"
- Add items like:
  - "Defeat Margit, The Fell Omen"
  - "Find all Sites of Grace in Limgrave"
  - "Collect all Legendary Armaments"
- Repeat to add more items

### 5. View Your Checklists
- Click "My Checklists"
- See two sections:
  - **Created by Me**: Your original checklists
  - **My Progress Tracking**: Checklists you've copied from others

### 6. Browse Community Checklists
- Click "Browse" in the navigation
- See all public checklists from the community
- Use the search box to filter by game name
- Click on any checklist to view it

### 7. Copy a Community Checklist
- Find a public checklist (or use the one you created)
- Click "Copy to My Checklists"
- The checklist is now in your account for progress tracking

### 8. Track Your Progress
- Go to "My Checklists"
- Click on a copied checklist
- Check off items as you complete them
- Watch your progress percentage increase!

## Example Use Cases

### Use Case 1: RPG 100% Completion
Create checklists for:
- All boss fights
- Hidden items and collectibles
- Side quests
- Achievements/trophies

### Use Case 2: Competitive Game Rank Progression
Track:
- Skills to master
- Characters to learn
- Rank milestones
- Game knowledge checkpoints

### Use Case 3: Game Collection Management
Organize:
- Games to play
- Games completed
- DLC/expansions owned
- Favorite games to replay

### Use Case 4: Community Challenge
Share:
- Speedrun route checklists
- Challenge mode guides
- No-damage run checklists
- Themed playthroughs

## Features Demonstrated

✅ **User Authentication**: Secure login and registration  
✅ **Create Content**: Build custom checklists for any game  
✅ **Share Content**: Make checklists public for the community  
✅ **Fork Content**: Copy others' checklists to your account  
✅ **Track Progress**: Check off items and see completion percentage  
✅ **Search & Browse**: Find checklists by game name  
✅ **Privacy Control**: Keep checklists private or share them  

## Tips & Tricks

- **Organize Items**: Use clear, descriptive titles for checklist items
- **Add Details**: Use the description field to add helpful notes
- **Public vs Private**: Keep work-in-progress checklists private, share when complete
- **Search**: Use specific game names for better search results
- **Progress Tracking**: Copy checklists early to track from the beginning

## Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

All 10 tests should pass, covering:
- User registration and login
- Checklist creation
- Progress tracking
- Browse functionality
- Security features

Enjoy using Game Checklist Progresser!
