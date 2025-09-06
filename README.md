# VR 180 Video Processing Platform

A scalable FastAPI backend for converting 2D videos to immersive VR 180° format using AI-powered depth estimation. This platform serves a Builder.io frontend deployed on Vercel and is designed for deployment on Google Cloud Run.

## Features

- **User Authentication**: Firebase Auth integration with JWT token validation
- **Video Upload**: Direct upload to Google Cloud Storage with signed URLs
- **AI-Powered Conversion**: 2D to VR 180° conversion using MiDaS depth estimation
- **Asynchronous Processing**: Cloud Tasks for scalable job queue management
- **Real-time Status**: Firestore for job status tracking and progress updates
- **RESTful APIs**: Complete API for frontend integration
- **Production Ready**: Docker containerization and Cloud Run deployment

## Technical Stack

- **Backend**: FastAPI (Python 3.9+)
- **Authentication**: Firebase Admin SDK
- **Database**: Firestore
- **Storage**: Google Cloud Storage
- **Job Queue**: Google Cloud Tasks
- **AI Processing**: MiDaS + FFmpeg + OpenCV
- **Deployment**: Google Cloud Run

## API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication
- `GET /auth/profile` - Get user profile
- `PUT /auth/profile` - Update user profile
- `POST /auth/logout` - User logout
- `DELETE /auth/account` - Delete user account

### Video Management
- `POST /videos/upload` - Generate upload URL
- `POST /videos/convert` - Queue video conversion
- `GET /videos/status/{job_id}` - Get conversion status
- `GET /videos/{video_id}` - Get video information
- `GET /videos/download/{video_id}` - Get download URL
- `GET /videos/preview/{video_id}` - Get VR preview URLs
- `GET /videos/user/{user_id}` - Get user's videos
- `DELETE /videos/{video_id}` - Delete video

### System
- `GET /health` - Health check
- `GET /metrics` - System metrics
- `GET /system/status` - System status

## Quick Start

### Prerequisites

- Python 3.9+
- Google Cloud Project with enabled APIs:
  - Cloud Storage
  - Cloud Tasks
  - Firestore
- Firebase Project with Authentication enabled

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd vr-180-video-processing
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Set up Firebase**
   - Create a Firebase project
   - Enable Authentication
   - Download service account key
   - Set `FIREBASE_PROJECT_ID` and `FIREBASE_SERVICE_ACCOUNT_KEY_PATH`

5. **Set up Google Cloud**
   - Create a GCS bucket
   - Enable required APIs
   - Set up service account with necessary permissions
   - Configure `GOOGLE_CLOUD_PROJECT_ID` and `GOOGLE_CLOUD_STORAGE_BUCKET`

6. **Run the application**
   ```bash
   python -m app.main
   ```

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -t vr180-video-processing .
   ```

2. **Run the container**
   ```bash
   docker run -p 8000:8000 --env-file .env vr180-video-processing
   ```

### Google Cloud Run Deployment

1. **Build and push to Container Registry**
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT-ID/vr180-video-processing
   ```

2. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy vr180-video-processing \
     --image gcr.io/PROJECT-ID/vr180-video-processing \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars="ENVIRONMENT=production"
   ```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FIREBASE_PROJECT_ID` | Firebase project ID | Yes |
| `FIREBASE_SERVICE_ACCOUNT_KEY_PATH` | Path to Firebase service account key | Yes |
| `GOOGLE_CLOUD_PROJECT_ID` | Google Cloud project ID | Yes |
| `GOOGLE_CLOUD_STORAGE_BUCKET` | GCS bucket name | Yes |
| `ALLOWED_ORIGINS` | CORS allowed origins | Yes |
| `SECRET_KEY` | Application secret key | Yes |

### Firebase Setup

1. Create a Firebase project
2. Enable Authentication with Email/Password
3. Create a service account and download the key
4. Set up Firestore database
5. Configure security rules

### Google Cloud Setup

1. Create a GCS bucket for video storage
2. Enable Cloud Tasks API
3. Create a service account with roles:
   - Storage Admin
   - Cloud Tasks Admin
   - Firestore User
4. Set up Cloud Tasks queues

## API Usage Examples

### User Registration
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123",
    "display_name": "John Doe"
  }'
```

### Video Upload
```bash
curl -X POST "http://localhost:8000/videos/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "video.mp4",
    "content_type": "video/mp4",
    "file_size": 10485760,
    "title": "My Video"
  }'
```

### Video Conversion
```bash
curl -X POST "http://localhost:8000/videos/convert" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "video-uuid",
    "conversion_settings": {
      "resolution": "1080p",
      "quality": "high",
      "stereo_mode": "side-by-side"
    }
  }'
```

## Development

### Project Structure
```
app/
├── main.py                 # FastAPI application
├── config.py              # Configuration management
├── models/                # Pydantic models
│   ├── auth.py
│   ├── video.py
│   └── system.py
├── routes/                # API routes
│   ├── auth.py
│   ├── videos.py
│   ├── system.py
│   └── internal.py
├── services/              # Business logic
│   ├── firebase_service.py
│   ├── gcs_service.py
│   ├── cloud_tasks_service.py
│   ├── video_processing_service.py
│   └── firestore_service.py
├── middleware/            # Custom middleware
│   ├── auth_middleware.py
│   ├── cors_middleware.py
│   └── rate_limit_middleware.py
└── utils/                 # Utility functions
```

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

## Monitoring and Logging

The application includes comprehensive logging and monitoring:

- **Structured Logging**: JSON-formatted logs for production
- **Health Checks**: `/health` endpoint for load balancer
- **Metrics**: `/metrics` endpoint for monitoring
- **Error Tracking**: Comprehensive error handling and reporting

## Security

- **Authentication**: Firebase JWT token validation
- **Authorization**: User-based access control
- **Rate Limiting**: Per-endpoint rate limiting
- **CORS**: Configurable cross-origin resource sharing
- **Input Validation**: Pydantic model validation
- **Secure Headers**: Security headers middleware

## Performance

- **Async Processing**: Asynchronous video processing
- **Job Queue**: Scalable Cloud Tasks integration
- **Caching**: Efficient data caching strategies
- **Resource Management**: Memory and CPU optimization
- **Load Balancing**: Cloud Run auto-scaling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the API examples

## Roadmap

- [ ] WebSocket support for real-time updates
- [ ] Batch video processing
- [ ] Advanced AI models for depth estimation
- [ ] Video preview generation
- [ ] Analytics dashboard
- [ ] Multi-tenant support
- [ ] API versioning
- [ ] GraphQL endpoint
