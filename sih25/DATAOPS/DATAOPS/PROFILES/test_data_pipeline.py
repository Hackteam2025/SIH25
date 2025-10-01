
import asyncio
from sih25.LOADER.database import get_db_manager
from sih25.DATAOPS import step3_schema_explorer

async def check_database():
    try:
        db_manager = await get_db_manager()

        # Check floats
        async with db_manager.get_connection() as conn:
            floats = await conn.fetch('SELECT wmo_id FROM floats LIMIT 5')
            print(f'Floats in database: {len(floats)}')
            for float_record in floats:
                print(f'  - {float_record["wmo_id"]}')

        # Check profiles
        async with db_manager.get_connection() as conn:
            profiles = await conn.fetch('SELECT profile_id, float_wmo_id FROM profiles LIMIT 5')
            print(f'Profiles in database: {len(profiles)}')
            for profile in profiles:
                print(f'  - {profile["profile_id"]} (float: {profile["float_wmo_id"]})')

        # Check observations
        async with db_manager.get_connection() as conn:
            obs_count = await conn.fetchval('SELECT COUNT(*) FROM observations')
            obs_sample = await conn.fetch('SELECT parameter, COUNT(*) as count FROM observations GROUP BY parameter')
            print(f'Total observations: {obs_count}')
            print('Parameters:')
            for obs in obs_sample:
                print(f'  - {obs["parameter"]}: {obs["count"]} measurements')

        return True
    except Exception as e:
        print(f'Database check failed: {e}')
        return False

success = asyncio.run(check_database())
print(f'Database check: {"PASSED" if success else "FAILED"}')
