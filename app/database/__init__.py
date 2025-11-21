from app.Config import ENV_SETTINGS
from app.database.connections.supabase import Supabase

supabase = Supabase()
supabase.init_connection(ENV_SETTINGS.SUPABASE_URL, ENV_SETTINGS.SUPABASE_ANON_KEY, ENV_SETTINGS.SUPABASE_SERVICE_ROLE_KEY)
