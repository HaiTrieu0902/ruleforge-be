# PostgreSQL Setup Guide

## Windows Installation

### 1. Install PostgreSQL

**Option A: Download from official website**
1. Go to https://www.postgresql.org/download/windows/
2. Download the installer for Windows
3. Run the installer
4. During installation:
   - Set password for postgres user: `040202005173`
   - Keep default port: `5432`
   - Remember the installation path

**Option B: Using Chocolatey (if you have it)**
```powershell
choco install postgresql
```

### 2. Create the Database

After PostgreSQL is installed and running:

**Option A: Using pgAdmin (GUI)**
1. Open pgAdmin (installed with PostgreSQL)
2. Connect to PostgreSQL server
3. Right-click on "Databases" → "Create" → "Database"
4. Name: `ruleforge`
5. Click "Save"

**Option B: Using Command Line**
```cmd
# Open Command Prompt as Administrator
createdb -U postgres ruleforge
```

**Option C: Using SQL**
```sql
-- Connect to PostgreSQL and run:
CREATE DATABASE ruleforge;
```

### 3. Verify Setup

Run the connection test:
```cmd
cd D:\learning\ruleforge-be
python test_connection.py
```

You should see:
```
✅ PostgreSQL connection successful!
Server version: PostgreSQL 15.x...
```

### 4. Create Tables

Run the table creation script:
```cmd
python create_tables.py
```

You should see:
```
🗄️  Creating database tables...
✅ Documents table created/verified
✅ Summaries table created/verified  
✅ Rules table created/verified
✅ Database indexes created/verified
🎉 Database tables created successfully!
```

## Troubleshooting

### Connection Failed
- **Check if PostgreSQL is running**: Look for "postgresql" service in Task Manager
- **Check port**: Make sure PostgreSQL is running on port 5432
- **Check password**: Ensure postgres user password is `040202005173`
- **Check database exists**: Make sure `ruleforge` database exists

### Permission Denied
- Make sure postgres user has permission to create databases
- Try running Command Prompt as Administrator

### Service Not Running
```cmd
# Start PostgreSQL service
net start postgresql-x64-15
```
(Replace `postgresql-x64-15` with your actual service name)

## Default Connection Settings

The application is configured with these settings:
- **Host**: localhost
- **Port**: 5432
- **Database**: ruleforge
- **Username**: postgres
- **Password**: 040202005173

These are set in `.env` file and can be modified if needed.