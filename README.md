# Image Processing System

A Flask-based computer vision application that leverages Meta's Segment Anything Model (SAM) for intelligent scene analysis and component detection. The system processes room scenes, identifies individual components, and manages the data through a PostgreSQL database.

## Key Features
- Automated scene component detection using SAM
- Modular processing pipeline for image analysis
- RESTful API endpoints with Flask
- PostgreSQL database with SQLAlchemy ORM
- HTMX-powered frontend for real-time interactions
- Comprehensive test suite
- Error logging and monitoring

## Tech Stack
- **Backend Framework**: Flask
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Computer Vision**: Meta's Segment Anything Model (SAM)
- **Frontend**: HTMX & Tailwind CSS
- **Database Migrations**: Flask-Migrate
- **Testing**: Python unittest & pytest

## Prerequisites
- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)
- Virtual environment (recommended)

## Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/modular-scene-processing.git
cd modular-scene-processing
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
# Create .env file and add the following variables
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=modular_scenes
TEST_DB_NAME=modular_scenes_test
```

5. Initialize the database
```bash
# Create PostgreSQL databases
createdb modular_scenes
createdb modular_scenes_test

# Run migrations
flask db upgrade
```

## Project Structure
```
modular-scenes-mvp/
├── app/                       # Application package
│   ├── processing/           # Scene processing logic
│   ├── templates/            # HTML templates
│   ├── models.py            # Database models
│   └── routes.py            # API endpoints
├── tests/                    # Test suite
├── migrations/               # Database migrations
├── storage/                  # File storage
├── logs/                     # Application logs
└── instance/                # Instance-specific files
```

## Usage

1. Start the development server
```bash
python run.py
```

2. Access the admin interface at `http://localhost:5000/admin`

3. Upload a room scene image for processing

4. Review detected components in the admin interface

## API Endpoints

### Admin Routes
- `POST /admin/upload` - Upload new scene
- `GET /admin/processing` - View processing status
- `GET /admin/scene/<id>` - View scene details

### API Routes
- `POST /api/component/<id>/accept` - Accept detected component
- `POST /api/component/<id>/reject` - Reject detected component
- `GET /api/scene/<id>/statistics` - Get scene statistics

## Testing

Run the test suite:
```bash
python -m pytest
```

For coverage report:
```bash
coverage run -m pytest
coverage report
```

## Development Guidelines

1. Follow PEP 8 style guide
2. Write tests for new features
3. Update requirements.txt when adding dependencies
4. Use meaningful commit messages
5. Document new features and API changes

## Error Handling

- Application errors are logged in `logs/processing_errors_*.log`
- Database errors are handled with proper rollback
- File processing errors are logged with relevant metadata

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details

## Acknowledgments

- [Meta Segment Anything Model (SAM)](https://segment-anything.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [HTMX](https://htmx.org/)

## Development Status
🚧 Active Development

## Contact

Your Name - [@yourtwitter](https://twitter.com/yourtwitter)
Project Link: [https://github.com/yourusername/modular-scene-processing](https://github.com/yourusername/modular-scene-processing)
