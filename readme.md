# Agora - Parliamentary Proceedings Analysis

## Overview
Agora is a web application that makes Cypriot parliamentary proceedings more accessible and understandable. It allows users to explore parliamentary sessions, view summaries, analyze legislative topics, and ask questions about the proceedings.

## Features
- 📄 **Session Browser**: Browse and access parliamentary session documents
- 📝 **Smart Summaries**: Get concise summaries of parliamentary sessions
- 📊 **Legislative Analysis**: View structured breakdowns of legislative topics discussed
- ❓ **Interactive Q&A**: Ask questions about any session's contents
- 🔍 **PDF Integration**: Direct access to original PDF documents

## Technology Stack
- **Backend**: Python 3.x, Django
- **Frontend**: HTML5, Bootstrap 5, JavaScript
- **AI/ML**: Google Gemini Pro
- **Database**: SQLite (default)
- **PDF Processing**: PyPDF2

## Installation

1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies
4. Set up environment variables - `GEMINI_API_KEY=your_api_key_here`
5. Create .env file in the root directory
6. Run migrations - `python manage.py migrate`
7. Start the development server - `python manage.py runserver`


## Usage
1. Place parliamentary PDF documents in the `media/pdf_documents/` directory
2. Access the application at `http://localhost:8000`
3. Browse available sessions
4. View summaries and legislative topics
5. Ask questions about specific sessions

## API Endpoints
- `GET /`: Session list view
- `GET /session/<filename>/`: Session detail view
- `GET /session/<filename>/topics/`: Get session topics
- `POST /session/<filename>/`: Submit Q&A queries

## Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.



## Contact
Pieris Christofi - [@christofip](https://github.com/christofip)

Project Link: [https://github.com/christofip/agora](https://github.com/christofip/agora)