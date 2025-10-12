#!/usr/bin/env python3
"""
Database Initialization Script
Creates necessary tables in PostgreSQL
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.config import settings
from app.services.database import metadata, database


async def create_tables():
    """Create all database tables"""
    print("🔧 Initializing database...")
    print(
        f"📊 Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    try:
        # Create engine
        engine = create_engine(settings.DATABASE_URL)

        # Drop existing tables (optional, comment out in production)
        print("⚠️  Dropping existing tables...")
        metadata.drop_all(engine)

        # Create tables
        print("📦 Creating tables...")
        metadata.create_all(engine)

        print("✅ Tables created successfully!")

        # List created tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
            """))

            tables = [row[0] for row in result]
            print(f"\n📋 Created tables: {', '.join(tables)}")

        # Create indexes
        print("\n🔍 Creating indexes...")
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversations_session_id 
                ON conversations(session_id);
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversations_status 
                ON conversations(status);
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
                ON messages(conversation_id);
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_messages_created_at 
                ON messages(created_at DESC);
            """))

            conn.commit()

        print("✅ Indexes created successfully!")

        # Test connection with databases library
        print("\n🧪 Testing async connection...")
        await database.connect()
        result = await database.fetch_one("SELECT 1 as test")
        print(f"✅ Async connection test: {result['test']}")
        await database.disconnect()

        print("\n🎉 Database initialization complete!")

    except Exception as e:
        print(f"\n❌ Error initializing database: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def seed_test_data():
    """Insert test data (optional)"""
    print("\n🌱 Seeding test data...")

    try:
        await database.connect()

        # Insert a test conversation
        test_conversation = {
            "conversation_id": "conv-test-12345",
            "session_id": "test-session-001",
            "dify_conversation_id": "dify-conv-test",
            "status": "active",
            "initial_context": {
                "session_id": "test-session-001",
                "user_data": {
                    "is_identified_user": True,
                    "name": "Test User",
                    "email": "test@example.com"
                },
                "traffic_data": {
                    "traffic_source": "direct",
                    "landing_page": "/test"
                }
            },
            "message_count": 0
        }

        from app.services.database import conversations_table
        query = conversations_table.insert().values(**test_conversation)
        await database.execute(query)

        print("✅ Test data seeded successfully!")

        await database.disconnect()

    except Exception as e:
        print(f"⚠️  Seeding failed (might already exist): {str(e)}")


def check_prerequisites():
    """Check if prerequisites are met"""
    print("🔍 Checking prerequisites...")

    # Check if .env file exists
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        print("❌ .env file not found!")
        print("📝 Copy .env.example to .env and configure it")
        sys.exit(1)

    print("✅ .env file found")

    # Check if database URL is set
    if not settings.DATABASE_URL or "password" in settings.DATABASE_URL.lower() and "@" not in settings.DATABASE_URL:
        print("❌ DATABASE_URL not properly configured in .env")
        print("📝 Format: postgresql://user:password@host:port/database")
        sys.exit(1)

    print("✅ DATABASE_URL configured")

    print()


def main():
    """Main function"""
    print("=" * 60)
    print("  Quotebot AI Proxy - Database Initialization")
    print("=" * 60)
    print()

    check_prerequisites()

    # Run initialization
    asyncio.run(create_tables())

    # Ask if user wants to seed test data
    response = input("\n🌱 Seed test data? (y/n): ").strip().lower()
    if response == 'y':
        asyncio.run(seed_test_data())

    print("\n" + "=" * 60)
    print("✅ Setup complete! You can now run the application:")
    print("   uvicorn app.main:app --reload")
    print("=" * 60)


if __name__ == "__main__":
    main()
