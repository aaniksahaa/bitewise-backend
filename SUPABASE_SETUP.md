# Supabase Setup for Image Uploads

This guide will help you set up Supabase Storage for image uploads in the Bitewise API.

## Prerequisites

1. A Supabase account (free tier includes 1GB storage)
2. Basic understanding of environment variables

## Supabase Setup Steps

### 1. Create a Supabase Project

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Click "New project"
3. Choose your organization (or create one)
4. Enter project details:
   - Name: `bitewise-storage` (or your preferred name)
   - Database Password: Choose a strong password
   - Region: Select the closest to your users
5. Click "Create new project"
6. Wait for the project to be set up (usually takes 1-2 minutes)

### 2. Get Project Credentials

1. In your project dashboard, go to "Settings" → "API"
2. Copy the following values:
   - **Project URL** (looks like `https://your-project-ref.supabase.co`)
   - **anon/public key** (for client-side operations)
   - **service_role key** (for server-side operations - **keep this secret**)

### 3. Enable Storage

1. In your project dashboard, go to "Storage" in the left sidebar
2. Storage should already be enabled by default
3. You'll see the storage interface with buckets

### 4. Create Storage Bucket

You can either:

**Option A: Create manually in dashboard:**
1. Click "Create a new bucket"
2. Name: `chat-images` (or match your `SUPABASE_BUCKET_NAME` env var)
3. Set to "Public bucket" if you want direct URL access
4. Click "Create bucket"

**Option B: Let the code create it automatically:**
- The `SupabaseStorageService.create_bucket_if_not_exists()` method will create it for you

### 5. Configure Storage Policies (Important for Security)

1. Go to "Storage" → "Policies"
2. For the `chat-images` bucket, create policies:

**Insert Policy (Upload):**
```sql
-- Allow authenticated users to upload to their own folder
CREATE POLICY "Users can upload to own folder" ON storage.objects
FOR INSERT WITH CHECK (
  auth.role() = 'authenticated' 
  AND bucket_id = 'chat-images'
  AND (storage.foldername(name))[1] = auth.uid()::text
);
```

**Select Policy (Download):**
```sql
-- Allow public read access to all images
CREATE POLICY "Public read access" ON storage.objects
FOR SELECT USING (bucket_id = 'chat-images');
```

**Delete Policy (Optional):**
```sql
-- Allow users to delete their own files
CREATE POLICY "Users can delete own files" ON storage.objects
FOR DELETE USING (
  auth.role() = 'authenticated' 
  AND bucket_id = 'chat-images'
  AND (storage.foldername(name))[1] = auth.uid()::text
);
```

### 6. Configure Environment Variables

Add these variables to your `.env` file:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your_service_role_key_here
SUPABASE_BUCKET_NAME=chat-images

# File Upload Settings (optional)
MAX_FILE_SIZE_MB=10
```

**Important Notes:**
- Use the **service_role key** for `SUPABASE_KEY` (not the anon key)
- The service_role key bypasses RLS policies, so keep it secure
- Never expose the service_role key in client-side code

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Your Supabase project URL | `https://abc123.supabase.co` |
| `SUPABASE_KEY` | Service role key (server-side) | `eyJ0eXAiOiJKV1QiLCJhbGciOi...` |
| `SUPABASE_BUCKET_NAME` | Storage bucket name | `chat-images` |
| `MAX_FILE_SIZE_MB` | Maximum file size in MB | `10` |

## Testing the Setup

1. Install the new dependencies:
   ```bash
   pip install supabase Pillow python-magic
   ```

2. Start your FastAPI server:
   ```bash
   python run.py
   ```

3. Test image upload endpoint:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/chat/upload-image" \
        -H "Authorization: Bearer YOUR_TOKEN" \
        -F "image=@path/to/your/image.jpg"
   ```

## API Endpoints

### Upload Image Only
- **POST** `/api/v1/chat/upload-image`
- Uploads an image and returns the URL and metadata

### Chat with Images
- **POST** `/api/v1/chat/chat-with-images`
- Send a chat message with optional image attachments
- Uses form data: `message` (text) and `images` (files)

## File Structure

```
your-project/
├── .env                         # Environment variables
├── app/
│   ├── services/
│   │   └── supabase_storage.py  # Supabase storage service
│   └── api/endpoints/
│       └── chat.py              # Updated chat endpoints
└── requirements.txt             # Updated dependencies
```

## Storage Structure

Files will be organized in Supabase Storage as:
```
chat-images/
├── {user_id}/
│   └── {year}/{month}/{day}/
│       ├── {uuid}.jpg
│       ├── {uuid}.png
│       └── ...
```

## Security Best Practices

1. **Environment Variables:**
   - Never commit your service_role key to version control
   - Use different keys for development and production
   - Rotate keys periodically

2. **Storage Policies:**
   - Implement proper RLS (Row Level Security) policies
   - Restrict uploads to authenticated users only
   - Consider user-specific folder access

3. **File Validation:**
   - Validate file types on both client and server
   - Set appropriate file size limits
   - Scan for malicious content if needed

4. **Access Control:**
   - Use anon key for client-side operations
   - Use service_role key only for server-side operations
   - Consider implementing signed URLs for sensitive content

## Monitoring and Maintenance

1. **Storage Usage:**
   - Monitor storage usage in Supabase dashboard
   - Set up alerts for approaching limits
   - Free tier includes 1GB storage

2. **Performance:**
   - Use CDN if you have high traffic
   - Implement image optimization/compression
   - Consider thumbnail generation

## Troubleshooting

### Common Issues

1. **"Invalid bucket" errors:**
   - Ensure the bucket exists in your Supabase project
   - Check bucket name in environment variables
   - Verify bucket permissions

2. **"Permission denied" errors:**
   - Check your storage policies
   - Ensure you're using the correct API key
   - Verify user authentication

3. **"File upload failed" errors:**
   - Check file size limits
   - Verify file type restrictions
   - Ensure proper internet connectivity

4. **"Client initialization failed":**
   - Verify SUPABASE_URL and SUPABASE_KEY
   - Check environment variable loading
   - Ensure credentials are valid

### Supabase Storage Limits (Free Tier)

- **Storage:** 1GB
- **File upload size:** 50MB per file
- **Bandwidth:** 2GB/month
- **API requests:** 500,000/month

### Getting Help

- [Supabase Documentation](https://supabase.com/docs/guides/storage)
- [Supabase Storage API Reference](https://supabase.com/docs/reference/javascript/storage-from-upload)
- [Supabase Community Discord](https://discord.supabase.com/)
- Check Supabase dashboard logs for detailed error messages 