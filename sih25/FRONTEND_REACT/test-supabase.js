// Quick test script to verify Supabase connection
// Run this to check if your Supabase is accessible

const SUPABASE_URL = 'https://ampdkmvvytxlrdtmvmqv.supabase.co'
// You need to get the anon key from: https://app.supabase.com/project/ampdkmvvytxlrdtmvmqv/settings/api

async function testConnection() {
  try {
    console.log('Testing Supabase connection...')

    // Test basic connectivity
    const response = await fetch(`${SUPABASE_URL}/rest/v1/`, {
      headers: {
        'apikey': 'YOUR_ANON_KEY_HERE',
        'Authorization': 'Bearer YOUR_ANON_KEY_HERE'
      }
    })

    console.log('Response status:', response.status)

    if (response.ok) {
      console.log('✅ Supabase connection successful!')

      // Test profiles table
      const profilesResponse = await fetch(`${SUPABASE_URL}/rest/v1/profiles?limit=1`, {
        headers: {
          'apikey': 'YOUR_ANON_KEY_HERE',
          'Authorization': 'Bearer YOUR_ANON_KEY_HERE'
        }
      })

      if (profilesResponse.ok) {
        const data = await profilesResponse.json()
        console.log('✅ Profiles table accessible!')
        console.log('Sample data:', data)
      } else {
        console.log('❌ Profiles table not accessible')
      }

    } else {
      console.log('❌ Supabase connection failed')
    }
  } catch (error) {
    console.error('❌ Error:', error)
  }
}

// Uncomment to test:
// testConnection()

console.log(`
🔑 TO GET YOUR SUPABASE ANON KEY:

1. Go to: https://app.supabase.com/project/ampdkmvvytxlrdtmvmqv/settings/api
2. Copy the "anon public" key
3. Replace YOUR_ANON_KEY_HERE in the .env file

Or check your Supabase dashboard under Settings > API
`)

export { testConnection }