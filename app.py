from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import cv2
import numpy as np
import os
from werkzeug.utils import secure_filename
import time
from ultralytics import YOLO

app = Flask(__name__)
CORS(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize YOLOv8 Pose model
model = YOLO('yolov8n-pose.pt')  # Using nano model for speed, can use larger models for better accuracy

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_frame(frame):
    try:
        # Run YOLOv8 inference
        results = model(frame, verbose=False)[0]
        
        # Draw keypoints on frame
        annotated_frame = results.plot()
        
        # Extract keypoints
        keypoints = []
        if results.keypoints is not None:
            for person_keypoints in results.keypoints.data:
                # Convert keypoints to list of dictionaries
                person_points = []
                for kp in person_keypoints:
                    x, y, conf = kp.tolist()
                    person_points.append({
                        'x': float(x),
                        'y': float(y),
                        'confidence': float(conf)
                    })
                keypoints.append(person_points)
        
        return annotated_frame, keypoints
        
    except Exception as e:
        print(f"Error in process_frame: {str(e)}")
        raise

def generate_frames(video_path):
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # Process frame and draw landmarks
        processed_frame, keypoints = process_frame(frame)
        
        # Encode the frame
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        frame = buffer.tobytes()
        
        # Add frame count to ensure monotonically increasing timestamps
        frame_count += 1
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        # Add a small delay to control frame rate
        time.sleep(0.03)  # approximately 30 FPS
    
    cap.release()

@app.route('/video_feed/<filename>')
def video_feed(filename):
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return Response(generate_frames(video_path),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

def calculate_pose_similarity(reference_keypoints, user_keypoints):
    """
    Calculate similarity between two poses using keypoints
    Returns a similarity score between 0 and 1
    """
    if not reference_keypoints or not user_keypoints:
        return 0
    
    # For now, compare only the first person detected in each frame
    # TODO: Implement multi-person comparison
    ref_points = reference_keypoints[0] if reference_keypoints else []
    user_points = user_keypoints[0] if user_keypoints else []
    
    if not ref_points or not user_points:
        return 0
    
    # Calculate Euclidean distance between corresponding keypoints
    total_distance = 0
    valid_points = 0
    
    for ref_point, user_point in zip(ref_points, user_points):
        if ref_point['confidence'] > 0.5 and user_point['confidence'] > 0.5:
            dx = ref_point['x'] - user_point['x']
            dy = ref_point['y'] - user_point['y']
            
            # Calculate normalized distance
            distance = np.sqrt(dx*dx + dy*dy)
            total_distance += distance
            valid_points += 1
    
    if valid_points == 0:
        return 0
    
    # Normalize the distance and convert to similarity score
    avg_distance = total_distance / valid_points
    similarity = 1.0 / (1.0 + avg_distance)
    
    return similarity

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process video and save frames with keypoints
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                return jsonify({'error': 'Could not open video file'}), 400
            
            frame_count = 0
            keypoints_list = []
            
            # Get video properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            print(f"Processing video: {filename}")
            print(f"Video dimensions: {width}x{height}")
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                try:
                    # Process frame and get keypoints
                    processed_frame, keypoints = process_frame(frame)
                    
                    # Save processed frame
                    frame_path = f'frame_{frame_count}.jpg'
                    frame_filepath = os.path.join(app.config['UPLOAD_FOLDER'], frame_path)
                    cv2.imwrite(frame_filepath, processed_frame)
                    
                    if keypoints:
                        keypoints_list.append({
                            'frame': frame_count,
                            'keypoints': keypoints,
                            'frame_path': frame_path
                        })
                    
                    frame_count += 1
                    
                except Exception as e:
                    print(f"Error processing frame {frame_count}: {str(e)}")
                    continue
            
            cap.release()
            
            if not keypoints_list:
                return jsonify({'error': 'No poses detected in video'}), 400
            
            print(f"Successfully processed {frame_count} frames")
            print(f"Detected poses in {len(keypoints_list)} frames")
            
            return jsonify({
                'message': 'Video processed successfully',
                'keypoints': keypoints_list,
                'filename': filename
            })
        
        return jsonify({'error': 'Invalid file type'}), 400
        
    except Exception as e:
        print(f"Error in upload_video: {str(e)}")
        return jsonify({'error': f'Error processing video: {str(e)}'}), 500

@app.route('/compare', methods=['POST'])
def compare_dances():
    data = request.json
    reference_keypoints = data.get('reference_keypoints')
    user_keypoints = data.get('user_keypoints')
    
    if not reference_keypoints or not user_keypoints:
        return jsonify({'error': 'Missing keypoints data'}), 400
    
    # Compare poses frame by frame
    comparison_results = []
    for ref_frame, user_frame in zip(reference_keypoints, user_keypoints):
        similarity = calculate_pose_similarity(
            ref_frame['keypoints'],
            user_frame['keypoints']
        )
        
        comparison_results.append({
            'frame': ref_frame['frame'],
            'similarity': similarity,
            'reference_frame': ref_frame['frame_path'],
            'user_frame': user_frame['frame_path']
        })
    
    return jsonify({
        'message': 'Comparison complete',
        'results': comparison_results
    })

if __name__ == '__main__':
    # Create uploads directory if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True) 