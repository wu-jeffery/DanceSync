# DanceSync

DanceSync is a web application that helps users improve their dance moves by comparing their performance with professional reference videos. The application uses MediaPipe for pose detection and analysis.

## Features

- Upload and process reference dance videos
- Upload and process user dance videos
- Real-time pose detection using MediaPipe
- Comparison of dance moves between reference and user videos
- Beat detection and synchronization analysis (coming soon)

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create required directories:
```bash
mkdir uploads
mkdir static
mkdir templates
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Upload a reference dance video (professional dancer)
2. Upload your own dance video
3. Click the "Compare Dances" button to analyze the differences
4. View the analysis results and feedback

## Technical Details

- Backend: Python Flask
- Frontend: HTML, CSS, JavaScript
- Pose Detection: MediaPipe
- Audio Processing: Librosa (coming soon)

## Project Structure

```
danceSync/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── static/            # Static files
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
├── templates/         # HTML templates
│   └── index.html
└── uploads/          # Temporary video storage
```

## Contributing

Feel free to submit issues and enhancement requests! 