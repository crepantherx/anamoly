import os
from supabase import create_client, Client

# Ideally these should be in env vars, but for this demo we'll hardcode as requested
SUPABASE_URL = "https://xbxtsvprksycsneuvzbq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhieHRzdnBya3N5Y3NuZXV2emJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM4MDcwNzgsImV4cCI6MjA3OTM4MzA3OH0.uqmyIVk4Ac3CyyvxfIa0WaxGixheToixZSX-8s9cnW4"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
