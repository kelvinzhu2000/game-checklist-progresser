# Database Migration Guide

## Quick Start for Common Issues

### Error: "NOT NULL constraint failed: checklists.game_name"

If you see this error when creating a new checklist, your database has the old `game_name` column that needs to be removed. 

**Solution:**
```bash
# Backup your database first!
cp game_checklist.db game_checklist.db.backup

# Run the migration to fix the issue
python add_reward_tables_migration.py
```

This will automatically detect and remove the legacy `game_name` column while preserving all your data.

---

## Migrating from game_name to Game Model

This guide explains how to migrate an existing database from the old schema (where `Checklist` has a `game_name` string field) to the new schema (where `Checklist` has a `game_id` foreign key to the `Game` table).

### Why Migrate?

The new schema improves database query efficiency by:
- Using integer foreign keys instead of string comparisons
- Reducing data duplication (game names stored once instead of per checklist)
- Enabling more efficient indexing and joins
- Supporting future enhancements like game metadata

### Before You Begin

⚠️ **IMPORTANT: Backup your database before migrating!**

```bash
# For SQLite
cp game_checklist.db game_checklist.db.backup

# For PostgreSQL
pg_dump your_database > backup.sql

# For MySQL
mysqldump your_database > backup.sql
```

### Migration Steps

#### For New Installations

If you're starting fresh, no migration is needed. The new schema will be created automatically when you run the application.

#### For Existing Databases

If you have an existing database with checklists using `game_name`:

1. **Backup your database** (see above)

2. **Update your code** to the version with the Game model

3. **Run the game model migration script**:
   ```bash
   python migrate_to_game_model.py
   ```

4. **Run the reward system migration** (this also cleans up the legacy game_name column):
   ```bash
   python add_reward_tables_migration.py
   ```
   
   This script will:
   - Create the rewards and checklist_item_rewards tables
   - Automatically detect and remove the legacy `game_name` column if present
   - Preserve all your existing data

5. **Test your application** thoroughly after migration
   DROP INDEX IF EXISTS ix_checklists_game_name;
   ```

### What the Migration Does

The migration script performs these operations:

1. Creates the `games` table if it doesn't exist
2. Extracts all unique game names from the `checklists` table
3. Creates a `Game` record for each unique game name
4. Adds the `game_id` column to the `checklists` table
5. Populates `game_id` for all existing checklists based on their `game_name`
6. Creates an index on the `game_id` column for efficient queries
7. (Optional) Leaves the old `game_name` column in place for safety

### Manual Migration (Alternative)

If you prefer to migrate manually or the script doesn't work for your setup:

```sql
-- 1. Create the games table
CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- For SQLite
    -- id SERIAL PRIMARY KEY,                -- For PostgreSQL
    -- id INT AUTO_INCREMENT PRIMARY KEY,   -- For MySQL
    name VARCHAR(200) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create index on game name
CREATE INDEX ix_games_name ON games(name);

-- 3. Insert unique games from checklists
INSERT INTO games (name, created_at)
SELECT DISTINCT game_name, MIN(created_at)
FROM checklists
GROUP BY game_name;

-- 4. Add game_id column to checklists
ALTER TABLE checklists ADD COLUMN game_id INTEGER;

-- 5. Populate game_id from game_name
UPDATE checklists
SET game_id = (
    SELECT id FROM games WHERE games.name = checklists.game_name
);

-- 6. Create index on game_id
CREATE INDEX ix_checklists_game_id ON checklists(game_id);

-- 7. Add foreign key constraint (if supported)
-- For PostgreSQL/MySQL:
-- ALTER TABLE checklists 
-- ADD CONSTRAINT fk_checklists_game_id 
-- FOREIGN KEY (game_id) REFERENCES games(id);

-- 8. (Optional) Drop old game_name column after verification
-- ALTER TABLE checklists DROP COLUMN game_name;
-- DROP INDEX ix_checklists_game_name;
```

### Verification

After migration, verify everything works:

1. Start your application
2. Browse games - should display all your games
3. View checklists - should show correct game names
4. Create a new checklist - should work with game selection
5. Copy a checklist - should preserve game association

### Troubleshooting

**Problem: Migration script fails with "column already exists"**
- Solution: Your database might already be migrated. Check your schema.

**Problem: Game names appear as numbers or IDs**
- Solution: Check that templates are using `checklist.game.name` instead of `checklist.game_name`

**Problem: Can't find certain games**
- Solution: Verify all games were created: `SELECT * FROM games;`

**Problem: New checklists don't save**
- Solution: Check that your code creates Game records when needed (see `routes.py` create function)

### Rollback (If Needed)

If something goes wrong and you need to rollback:

1. Stop the application
2. Restore your backup:
   ```bash
   # For SQLite
   cp game_checklist.db.backup game_checklist.db
   
   # For PostgreSQL
   psql your_database < backup.sql
   
   # For MySQL
   mysql your_database < backup.sql
   ```
3. Revert your code to the previous version (before the Game model was added)
4. Restart the application

### Schema Comparison

**Old Schema:**
```
checklists:
  - id
  - title
  - game_name (VARCHAR)  ← String field
  - description
  - creator_id
  - is_public
  - created_at
  - updated_at
```

**New Schema:**
```
games:
  - id                     ← New table
  - name (VARCHAR, UNIQUE)
  - created_at

checklists:
  - id
  - title
  - game_id (INTEGER)      ← Foreign key to games.id
  - description
  - creator_id
  - is_public
  - created_at
  - updated_at
```

### Support

If you encounter issues during migration:
1. Check the migration script output for error messages
2. Verify your database engine and version compatibility
3. Review the troubleshooting section above
4. Open an issue on GitHub with details about your setup and the error
