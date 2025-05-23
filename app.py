from flask import Flask, request, jsonify, render_template, Response, send_from_directory
from flask_cors import CORS
import cv2
import numpy as np
import os
from werkzeug.utils import secure_filename
import time
from ultralytics import YOLO
from torch_setup import setup_torch_safe_globals
from audio_processor import compare_audio_similarity

# Setup PyTorch safe globals
setup_torch_safe_globals()

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

@app.route('/uploads/<filename>')
def serve_video(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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
            
            # Process video and save as new video with keypoints
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                return jsonify({'error': 'Could not open video file'}), 400
            
            # Get video properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            
            # Create output video writer
            processed_filename = f'processed_{filename}'
            processed_filepath = os.path.join(app.config['UPLOAD_FOLDER'], processed_filename)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(processed_filepath, fourcc, fps, (width, height))
            
            frame_count = 0
            keypoints_list = []
            
            print(f"Processing video: {filename}")
            print(f"Video dimensions: {width}x{height}, FPS: {fps}")
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                try:
                    # Process frame and get keypoints
                    processed_frame, keypoints = process_frame(frame)
                    
                    # Write processed frame to video
                    out.write(processed_frame)
                    
                    if keypoints:
                        keypoints_list.append({
                            'frame': frame_count,
                            'keypoints': keypoints
                        })
                    
                    frame_count += 1
                    
                except Exception as e:
                    print(f"Error processing frame {frame_count}: {str(e)}")
                    continue
            
            cap.release()
            out.release()
            
            if not keypoints_list:
                return jsonify({'error': 'No poses detected in video'}), 400
            
            print(f"Successfully processed {frame_count} frames")
            print(f"Detected poses in {len(keypoints_list)} frames")
            
            return jsonify({
                'message': 'Video processed successfully',
                'keypoints': keypoints_list,
                'filename': processed_filename,
                'original_filename': filename
            })
        
        return jsonify({'error': 'Invalid file type'}), 400
        
    except Exception as e:
        print(f"Error in upload_video: {str(e)}")
        return jsonify({'error': f'Error processing video: {str(e)}'}), 500

@app.route('/sync_audio', methods=['POST'])
def sync_audio():
    data = request.json
    reference_video = data.get('reference_video')
    user_video = data.get('user_video')
    
    if not reference_video or not user_video:
        return jsonify({'error': 'Missing video filenames'}), 400
    
    # Compare audio
    ref_video_path = os.path.join(app.config['UPLOAD_FOLDER'], reference_video)
    user_video_path = os.path.join(app.config['UPLOAD_FOLDER'], user_video)
    
    is_same_song, audio_similarity, time_offset, ref_beats, user_beats = compare_audio_similarity(
        ref_video_path, 
        user_video_path
    )
    
    if not is_same_song:
        return jsonify({
            'error': 'The videos appear to have different music. Please try with videos that have the same song.',
            'audio_similarity': audio_similarity
        }), 400
    
    return jsonify({
        'message': 'Videos synchronized successfully',
        'audio_similarity': audio_similarity,
        'time_offset': time_offset,
        'reference_beats': ref_beats.tolist(),
        'user_beats': user_beats.tolist()
    })

@app.route('/compare', methods=['POST'])
def compare_dances():
    data = request.json
    reference_keypoints = data.get('reference_keypoints')
    user_keypoints = data.get('user_keypoints')
    reference_video = data.get('reference_video')
    user_video = data.get('user_video')
    
    if not reference_keypoints or not user_keypoints:
        return jsonify({'error': 'Missing keypoints data'}), 400
    
    # Get beat timestamps
    ref_video_path = os.path.join(app.config['UPLOAD_FOLDER'], reference_video)
    user_video_path = os.path.join(app.config['UPLOAD_FOLDER'], user_video)
    
    _, _, _, ref_beats, user_beats = compare_audio_similarity(ref_video_path, user_video_path)
    
    # Compare poses at beat timestamps
    comparison_results = []
    
    # Convert frame numbers to timestamps
    fps = 30  # Assuming 30fps, adjust if different
    ref_frames = {int(frame['frame']): frame['keypoints'] for frame in reference_keypoints}
    user_frames = {int(frame['frame']): frame['keypoints'] for frame in user_keypoints}
    
    # Compare poses at each beat
    for ref_beat, user_beat in zip(ref_beats, user_beats):
        ref_frame = int(ref_beat * fps)
        user_frame = int(user_beat * fps)
        
        if ref_frame in ref_frames and user_frame in user_frames:
            similarity = calculate_pose_similarity(
                ref_frames[ref_frame],
                user_frames[user_frame]
            )
            
            comparison_results.append({
                'frame': ref_frame,
                'similarity': similarity,
                'timestamp': float(ref_beat)  # Convert numpy float to Python float
            })
    
    # Calculate average similarity
    if comparison_results:
        avg_similarity = sum(r['similarity'] for r in comparison_results) / len(comparison_results)
    else:
        avg_similarity = 0.0
    
    return jsonify({
        'message': 'Comparison complete',
        'results': comparison_results,
        'average_similarity': avg_similarity,
        'num_beats_analyzed': len(comparison_results)
    })

def calculate_pose_similarity(reference_keypoints, user_keypoints):
    """
    Calculate similarity between two poses using keypoints
    Returns a similarity score between 0 and 1
    """
    if not reference_keypoints or not user_keypoints:
        return 0
    
    # For now, compare only the first person detected in each frame
    ref_points = reference_keypoints[0] if reference_keypoints else []
    user_points = user_keypoints[0] if user_keypoints else []
    
    if not ref_points or not user_points:
        return 0
    
    # Convert points to numpy arrays for faster computation
    ref_coords = np.array([[p['x'], p['y']] for p in ref_points])
    user_coords = np.array([[p['x'], p['y']] for p in user_points])
    ref_conf = np.array([p['confidence'] for p in ref_points])
    user_conf = np.array([p['confidence'] for p in user_points])
    
    # Create mask for valid points (confidence > 0.5)
    valid_mask = (ref_conf > 0.5) & (user_conf > 0.5)
    
    if not np.any(valid_mask):
        return 0
    
    # Calculate distances only for valid points
    distances = np.sqrt(np.sum((ref_coords[valid_mask] - user_coords[valid_mask])**2, axis=1))
    avg_distance = np.mean(distances)
    
    # Normalize the distance and convert to similarity score
    similarity = 1.0 / (1.0 + avg_distance)
    
    return float(similarity)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Create uploads directory if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True) 