#!/usr/bin/env python3
"""
Test script to verify Supabase Storage configuration.
Run this to diagnose connection and permission issues.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def test_supabase_setup():
    """Test Supabase configuration and permissions."""
    
    print("🔍 Testing Supabase Configuration...")
    print("=" * 50)
    
    # Check environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") 
    bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "chat-images")
    
    print(f"SUPABASE_URL: {supabase_url}")
    print(f"SUPABASE_KEY: {'***' + supabase_key[-10:] if supabase_key and len(supabase_key) > 10 else 'NOT SET'}")
    print(f"SUPABASE_BUCKET_NAME: {bucket_name}")
    print()
    
    if not supabase_url or not supabase_key:
        print("❌ ERROR: Missing SUPABASE_URL or SUPABASE_KEY in environment variables")
        return False
    
    # Check if using service role key (should start with 'eyJ' and be longer)
    if supabase_key.startswith('eyJ') and len(supabase_key) > 100:
        print("✅ Using service role key (recommended for server-side)")
    else:
        print("⚠️  WARNING: Key might be anon/public key. Use service_role key for server operations.")
    
    try:
        # Create Supabase client
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully")
        
        # Test 1: List buckets
        print("\n📁 Testing bucket access...")
        try:
            buckets = supabase.storage.list_buckets()
            print(f"✅ Found {len(buckets)} buckets:")
            for bucket in buckets:
                print(f"   - {bucket.name} (public: {bucket.public})")
        except Exception as e:
            print(f"❌ Failed to list buckets: {e}")
            return False
        
        # Test 2: Check if our bucket exists
        bucket_exists = any(bucket.name == bucket_name for bucket in buckets)
        if bucket_exists:
            print(f"✅ Bucket '{bucket_name}' exists")
        else:
            print(f"⚠️  Bucket '{bucket_name}' does not exist")
            
            # Try to create bucket
            print("🔧 Attempting to create bucket...")
            try:
                result = supabase.storage.create_bucket(
                    bucket_name,
                    options={
                        "public": True,
                        "allowedMimeTypes": ["image/jpeg", "image/png", "image/gif", "image/webp"],
                        "fileSizeLimit": 10 * 1024 * 1024  # 10MB
                    }
                )
                print(f"✅ Bucket '{bucket_name}' created successfully")
            except Exception as e:
                print(f"❌ Failed to create bucket: {e}")
                if "already exists" in str(e).lower():
                    print("   (Bucket might already exist)")
                else:
                    return False
        
        # Test 3: Try to list files in bucket
        print(f"\n📂 Testing file listing in '{bucket_name}'...")
        try:
            files = supabase.storage.from_(bucket_name).list()
            print(f"✅ Can list files in bucket (found {len(files)} items)")
        except Exception as e:
            print(f"❌ Failed to list files: {e}")
            if "row-level security" in str(e).lower() or "unauthorized" in str(e).lower():
                print("   This suggests RLS (Row Level Security) policy issues")
                print("   Solution: Use service_role key or disable RLS for storage")
            return False
        
        # Test 4: Try to upload a test file
        print(f"\n⬆️  Testing file upload...")
        test_content = b"Hello Supabase Storage!"
        test_path = "test/hello.txt"
        
        try:
            response = supabase.storage.from_(bucket_name).upload(
                path=test_path,
                file=test_content,
                file_options={"content-type": "text/plain"}
            )
            print("✅ Test file uploaded successfully")
            
            # Test 5: Get public URL
            try:
                public_url = supabase.storage.from_(bucket_name).get_public_url(test_path)
                print(f"✅ Public URL generated: {public_url}")
            except Exception as e:
                print(f"⚠️  Could not get public URL: {e}")
                
        except Exception as e:
            print(f"❌ Failed to upload test file: {e}")
            # Try a different approach for upload
            try:
                print("🔄 Trying alternative upload method...")
                
                # Alternative upload method
                result = supabase.storage.from_(bucket_name).upload(
                    file=test_content,
                    path=test_path,
                    file_options={"content-type": "text/plain"}
                )
                print("✅ Alternative upload method worked!")
                
                # Get public URL
                try:
                    public_url = supabase.storage.from_(bucket_name).get_public_url(test_path)
                    print(f"✅ Public URL: {public_url}")
                except Exception as url_e:
                    print(f"⚠️  URL generation issue: {url_e}")
                    
            except Exception as e2:
                print(f"❌ Alternative upload also failed: {e2}")
                if "row-level security" in str(e2).lower():
                    print("   🔧 SOLUTION: This is an RLS issue. Here's how to fix it:")
                    print("   1. Go to your Supabase dashboard")
                    print("   2. Navigate to Storage > Policies")
                    print("   3. Either disable RLS for storage.objects table, or")
                    print("   4. Create appropriate policies for your bucket")
                    print("   5. Make sure you're using the service_role key (not anon key)")
                return False
        
        print("\n🎉 All tests passed! Supabase Storage is configured correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return False

if __name__ == "__main__":
    success = test_supabase_setup()
    if not success:
        print("\n🚨 Setup incomplete. Please fix the issues above before using the API.")
        exit(1)
    else:
        print("\n✅ Ready to use Supabase Storage in your API!") 