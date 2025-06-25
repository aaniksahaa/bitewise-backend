# Chat with Images API Documentation

## Overview
The Chat with Images API allows users to send messages along with image attachments and receive AI responses that can process and analyze the uploaded images. This endpoint handles both text and visual content, making it perfect for multimodal AI interactions.

## Endpoint Details

### Send Chat Message with Images
**POST** `/api/v1/chat/chat-with-images`

Send a chat message with optional image attachments and receive an AI response.

## Authentication
All requests require Bearer token authentication:
```
Authorization: Bearer <your_jwt_token>
```

## Request Format

### Content-Type
```
Content-Type: multipart/form-data
```

### Form Data Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | Yes | The text message content (1-10,000 characters) |
| `conversation_id` | integer | No | ID of existing conversation. If not provided, a new conversation will be created |
| `images` | File[] | No | Array of image files to upload with the message |

### Supported Image Formats
- **JPEG** (`.jpg`, `.jpeg`)
- **PNG** (`.png`)
- **WebP** (`.webp`)
- **GIF** (`.gif`)

### Image Constraints
- **Maximum file size**: 10MB per image
- **Maximum images per request**: 5 images
- **Supported dimensions**: Up to 4096x4096 pixels

## Response Format

### Success Response (201 Created)

```json
{
  "conversation_id": 123,
  "user_message": {
    "id": 456,
    "conversation_id": 123,
    "user_id": 789,
    "content": "What do you see in this image?",
    "is_user_message": true,
    "message_type": "image",
    "attachments": {
      "images": [
        {
          "url": "https://supabase-storage-url.com/image.jpg",
          "filename": "photo.jpg",
          "size": 1024000,
          "content_type": "image/jpeg",
          "storage_path": "chat_images/user_789/1234567890_photo.jpg",
          "metadata": {
            "file_size": 1024000,
            "upload_timestamp": "2024-01-15T10:30:00Z"
          }
        }
      ],
      "files": [],
      "widgets": null,
      "tool_results": null
    },
    "extra_data": {
      "has_images": true,
      "image_count": 1
    },
    "llm_model_id": null,
    "input_tokens": null,
    "output_tokens": null,
    "parent_message_id": null,
    "reactions": null,
    "status": "sent",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  "ai_message": {
    "id": 457,
    "conversation_id": 123,
    "user_id": 789,
    "content": "I can see a beautiful sunset over a mountain landscape. The image shows warm orange and pink hues in the sky, with silhouetted mountains in the foreground. The composition suggests this was taken during golden hour.",
    "is_user_message": false,
    "message_type": "text",
    "attachments": null,
    "extra_data": {
      "generated": true,
      "processed_images": true
    },
    "llm_model_id": 1,
    "input_tokens": 1250,
    "output_tokens": 180,
    "parent_message_id": null,
    "reactions": null,
    "status": "sent",
    "created_at": "2024-01-15T10:30:05Z",
    "updated_at": "2024-01-15T10:30:05Z"
  },
  "total_tokens_used": 1430,
  "cost_estimate": 0.0025
}
```

## Frontend Integration Examples

### JavaScript/TypeScript with Fetch API

```typescript
interface ChatWithImagesRequest {
  message: string;
  conversation_id?: number;
  images?: File[];
}

interface ChatResponse {
  conversation_id: number;
  user_message: Message;
  ai_message: Message;
  total_tokens_used: number;
  cost_estimate?: number;
}

async function sendChatWithImages(
  token: string,
  request: ChatWithImagesRequest
): Promise<ChatResponse> {
  const formData = new FormData();
  
  // Add text message
  formData.append('message', request.message);
  
  // Add conversation ID if provided
  if (request.conversation_id) {
    formData.append('conversation_id', request.conversation_id.toString());
  }
  
  // Add images if provided
  if (request.images && request.images.length > 0) {
    request.images.forEach((image, index) => {
      formData.append('images', image);
    });
  }
  
  const response = await fetch('/api/v1/chat/chat-with-images', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      // Don't set Content-Type header - let the browser set it for FormData
    },
    body: formData
  });
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to send message');
  }
  
  return response.json();
}

// Usage example
const fileInput = document.getElementById('fileInput') as HTMLInputElement;
const files = Array.from(fileInput.files || []);

try {
  const result = await sendChatWithImages(userToken, {
    message: "What do you see in these images?",
    conversation_id: currentConversationId,
    images: files
  });
  
  console.log('Chat response:', result);
  // Update UI with the response
} catch (error) {
  console.error('Error sending message:', error);
}
```

### React Hook Example

```tsx
import { useState, useCallback } from 'react';

interface UseChatWithImages {
  sendMessage: (message: string, images?: File[], conversationId?: number) => Promise<void>;
  loading: boolean;
  error: string | null;
}

export function useChatWithImages(token: string): UseChatWithImages {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const sendMessage = useCallback(async (
    message: string,
    images?: File[],
    conversationId?: number
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('message', message);
      
      if (conversationId) {
        formData.append('conversation_id', conversationId.toString());
      }
      
      if (images && images.length > 0) {
        images.forEach(image => {
          formData.append('images', image);
        });
      }
      
      const response = await fetch('/api/v1/chat/chat-with-images', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to send message');
      }
      
      const result = await response.json();
      // Handle successful response (e.g., update chat state)
      console.log('Message sent successfully:', result);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  }, [token]);
  
  return { sendMessage, loading, error };
}
```

### Vue.js Composition API Example

```vue
<script setup lang="ts">
import { ref } from 'vue';

const loading = ref(false);
const error = ref<string | null>(null);

async function sendChatWithImages(
  token: string,
  message: string,
  images?: File[],
  conversationId?: number
) {
  loading.value = true;
  error.value = null;
  
  try {
    const formData = new FormData();
    formData.append('message', message);
    
    if (conversationId) {
      formData.append('conversation_id', conversationId.toString());
    }
    
    if (images && images.length > 0) {
      images.forEach(image => {
        formData.append('images', image);
      });
    }
    
    const response = await fetch('/api/v1/chat/chat-with-images', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to send message');
    }
    
    const result = await response.json();
    return result;
    
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error occurred';
    throw err;
  } finally {
    loading.value = false;
  }
}
</script>
```

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "detail": "Failed to process image photo.jpg: File size exceeds maximum limit"
}
```

#### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

#### 413 Payload Too Large
```json
{
  "detail": "File too large"
}
```

#### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Failed to upload image: Storage service unavailable"
}
```

### Error Handling Best Practices

```typescript
async function handleChatWithImages(message: string, images: File[]) {
  try {
    const result = await sendChatWithImages(token, {
      message,
      images,
      conversation_id: currentConversationId
    });
    
    // Success handling
    updateChatHistory(result);
    
  } catch (error) {
    // Parse error response
    if (error instanceof Response) {
      const errorData = await error.json();
      
      switch (error.status) {
        case 400:
          showUserError('Invalid request: ' + errorData.detail);
          break;
        case 401:
          redirectToLogin();
          break;
        case 413:
          showUserError('File size too large. Please choose smaller images.');
          break;
        case 422:
          showValidationErrors(errorData.detail);
          break;
        default:
          showUserError('An unexpected error occurred. Please try again.');
      }
    } else {
      showUserError('Network error. Please check your connection.');
    }
  }
}
```

## Image Preview and Upload UI Examples

### React Image Upload Component

```tsx
import React, { useState, useRef } from 'react';

interface ImageUploadProps {
  onImagesSelected: (images: File[]) => void;
  maxImages?: number;
}

export function ImageUpload({ onImagesSelected, maxImages = 5 }: ImageUploadProps) {
  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    const validImages = files.filter(file => 
      file.type.startsWith('image/') && file.size <= 10 * 1024 * 1024
    );
    
    if (validImages.length + selectedImages.length > maxImages) {
      alert(`Maximum ${maxImages} images allowed`);
      return;
    }
    
    const newImages = [...selectedImages, ...validImages];
    setSelectedImages(newImages);
    onImagesSelected(newImages);
  };
  
  const removeImage = (index: number) => {
    const newImages = selectedImages.filter((_, i) => i !== index);
    setSelectedImages(newImages);
    onImagesSelected(newImages);
  };
  
  return (
    <div className="image-upload">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />
      
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={selectedImages.length >= maxImages}
      >
        Add Images ({selectedImages.length}/{maxImages})
      </button>
      
      <div className="image-previews">
        {selectedImages.map((image, index) => (
          <div key={index} className="image-preview">
            <img
              src={URL.createObjectURL(image)}
              alt={`Preview ${index + 1}`}
              style={{ width: 100, height: 100, objectFit: 'cover' }}
            />
            <button onClick={() => removeImage(index)}>×</button>
            <span>{image.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

## Rate Limiting and Best Practices

### Rate Limits
- **Requests per minute**: 60
- **Images per hour**: 300
- **Storage per user**: 1GB

### Best Practices

1. **Image Optimization**
   ```typescript
   // Compress images before upload
   function compressImage(file: File, maxWidth: number = 1024): Promise<File> {
     return new Promise((resolve) => {
       const canvas = document.createElement('canvas');
       const ctx = canvas.getContext('2d')!;
       const img = new Image();
       
       img.onload = () => {
         const ratio = Math.min(maxWidth / img.width, maxWidth / img.height);
         canvas.width = img.width * ratio;
         canvas.height = img.height * ratio;
         
         ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
         canvas.toBlob((blob) => {
           resolve(new File([blob!], file.name, { type: 'image/jpeg' }));
         }, 'image/jpeg', 0.8);
       };
       
       img.src = URL.createObjectURL(file);
     });
   }
   ```

2. **Progress Tracking**
   ```typescript
   function uploadWithProgress(formData: FormData, onProgress: (percent: number) => void) {
     return new Promise((resolve, reject) => {
       const xhr = new XMLHttpRequest();
       
       xhr.upload.addEventListener('progress', (e) => {
         if (e.lengthComputable) {
           const percent = (e.loaded / e.total) * 100;
           onProgress(percent);
         }
       });
       
       xhr.addEventListener('load', () => {
         if (xhr.status === 201) {
           resolve(JSON.parse(xhr.responseText));
         } else {
           reject(new Error(xhr.responseText));
         }
       });
       
       xhr.open('POST', '/api/v1/chat/chat-with-images');
       xhr.setRequestHeader('Authorization', `Bearer ${token}`);
       xhr.send(formData);
     });
   }
   ```

3. **Retry Logic**
   ```typescript
   async function sendWithRetry(
     formData: FormData,
     maxRetries: number = 3
   ): Promise<ChatResponse> {
     for (let attempt = 1; attempt <= maxRetries; attempt++) {
       try {
         const response = await fetch('/api/v1/chat/chat-with-images', {
           method: 'POST',
           headers: { 'Authorization': `Bearer ${token}` },
           body: formData
         });
         
         if (response.ok) {
           return response.json();
         }
         
         if (response.status < 500 || attempt === maxRetries) {
           throw new Error(`HTTP ${response.status}`);
         }
         
         // Wait before retry (exponential backoff)
         await new Promise(resolve => 
           setTimeout(resolve, Math.pow(2, attempt) * 1000)
         );
         
       } catch (error) {
         if (attempt === maxRetries) throw error;
       }
     }
     
     throw new Error('Max retries exceeded');
   }
   ```

## Testing the Endpoint

### cURL Example
```bash
curl -X POST "http://localhost:8000/api/v1/chat/chat-with-images" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "message=What do you see in this image?" \
  -F "conversation_id=123" \
  -F "images=@/path/to/image1.jpg" \
  -F "images=@/path/to/image2.png"
```

### Postman Collection
1. Set method to POST
2. URL: `{{baseUrl}}/api/v1/chat/chat-with-images`
3. Headers: `Authorization: Bearer {{token}}`
4. Body type: form-data
5. Add fields:
   - `message` (text): "Describe this image"
   - `conversation_id` (text): "123" (optional)
   - `images` (file): Select image files

This documentation should provide your frontend team with everything they need to properly integrate the chat with images functionality. The examples cover multiple frameworks and include proper error handling, optimization techniques, and best practices. 