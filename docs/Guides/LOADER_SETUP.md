# DATA LOADER Setup Guide

## Required Environment Variables

The DATA LOADER requires only **ONE essential environment variable**:

### ✅ **REQUIRED**
- **`DATABASE_URL`** - PostgreSQL connection string for Supabase

### ⚙️ **OPTIONAL** (have sensible defaults)
- `DB_MIN_CONNECTIONS` - Default: 2
- `DB_MAX_CONNECTIONS` - Default: 10
- `DB_MAX_INACTIVE_LIFETIME` - Default: 300.0

## Quick Setup

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Get your Supabase DATABASE_URL:**
   - Go to your Supabase project dashboard
   - Navigate to Settings → Database
   - Copy the "Connection string" under "Connection pooling"
   - It looks like: `postgresql://postgres.abc123:yourpassword@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`

3. **Update your .env file:**
   ```bash
   DATABASE_URL=postgresql://postgres.abc123:yourpassword@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
   ```

4. **Test the connection:**
   ```bash
   python -m sih25.LOADER.test_integration
   ```

## Database Schema

The DATA LOADER automatically creates these tables if they don't exist:

```sql
-- Floats table (one per float)
CREATE TABLE floats (
    wmo_id VARCHAR PRIMARY KEY,
    deployment_info JSONB,
    pi_details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Profiles table (one per profile/dive)
CREATE TABLE profiles (
    profile_id VARCHAR PRIMARY KEY,
    float_wmo_id VARCHAR REFERENCES floats(wmo_id),
    timestamp TIMESTAMP,
    latitude FLOAT,
    longitude FLOAT,
    position_qc INTEGER,
    data_mode CHAR(1),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Observations table (one per measurement)
CREATE TABLE observations (
    observation_id SERIAL PRIMARY KEY,
    profile_id VARCHAR REFERENCES profiles(profile_id),
    depth FLOAT,
    parameter VARCHAR,
    value FLOAT,
    qc_flag INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Usage Examples

```bash
# Process NetCDF to Parquet only (existing functionality)
python main_orchestrator.py data/D2900765_067.nc -o output

# Process NetCDF to Parquet AND load to database
python main_orchestrator.py data/D2900765_067.nc -o output --load-to-database

# Use ignore strategy for duplicates instead of upsert
python main_orchestrator.py data/D2900765_067.nc -o output --load-to-database --dedup-strategy ignore

# Don't auto-create tables (assume they exist)
python main_orchestrator.py data/D2900765_067.nc -o output --load-to-database --no-create-tables
```

## Troubleshooting

### Connection Issues
- Verify DATABASE_URL is correct
- Check if your IP is allowed in Supabase
- Ensure the database exists

### Permission Issues
- Verify your database user has CREATE TABLE permissions
- Check if the user can INSERT/UPDATE/SELECT

### Import Issues
- If you see "LOADER module not available", ensure you're running from the correct directory
- The module structure should be: `sih25/LOADER/`