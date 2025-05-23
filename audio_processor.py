import librosa
import numpy as np
from pydub import AudioSegment
import tempfile
import os
from scipy.spatial.distance import cosine
from scipy.signal import correlate
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_audio_from_video(video_path):
    """Extract audio from video file and return the audio path"""
    try:
        # Create a temporary file for the audio
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_audio.close()
        
        # Extract audio using pydub
        video = AudioSegment.from_file(video_path)
        video.export(temp_audio.name, format="wav")
        
        return temp_audio.name
    except Exception as e:
        logger.error(f"Error extracting audio from video {video_path}: {str(e)}")
        raise

def detect_beats(audio_path):
    """Detect beats in audio file and return beat timestamps."""
    try:
        # Extract audio from video first
        wav_path = extract_audio_from_video(audio_path)
        
        try:
            # Load audio with a lower sample rate for speed
            y, sr = librosa.load(wav_path, sr=22050)
            
            # Extract tempo and beats
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            
            # Convert tempo to float for logging
            tempo_float = float(tempo)
            logger.info(f"Detected tempo: {tempo_float:.1f} BPM")
            logger.info(f"Number of beats detected: {len(beat_times)}")
            
            return tempo_float, beat_times, y, sr
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(wav_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error detecting beats from {audio_path}: {str(e)}")
        raise

def find_time_offset(ref_audio, user_audio, sr):
    """Find the time offset between two audio signals using cross-correlation."""
    try:
        # Use cross-correlation to find the offset
        correlation = correlate(ref_audio, user_audio, mode='full')
        offset = np.argmax(correlation) - (len(ref_audio) - 1)
        
        # Convert offset to seconds
        offset_seconds = offset / sr
        
        logger.info(f"Raw offset in samples: {offset}")
        logger.info(f"Offset in seconds: {offset_seconds}")
        
        return offset_seconds
    except Exception as e:
        logger.error(f"Error finding time offset: {str(e)}")
        raise

def compare_audio_similarity(reference_path, user_path):
    """Compare audio similarity between two videos and find time offset."""
    try:
        logger.info(f"Comparing audio between {reference_path} and {user_path}")
        
        # Detect beats and get audio data
        ref_tempo, ref_beats, ref_audio, sr = detect_beats(reference_path)
        user_tempo, user_beats, user_audio, sr = detect_beats(user_path)
        
        # Log tempo comparison
        tempo_diff = abs(ref_tempo - user_tempo)
        logger.info(f"Reference tempo: {ref_tempo:.1f} BPM")
        logger.info(f"User tempo: {user_tempo:.1f} BPM")
        logger.info(f"Tempo difference: {tempo_diff:.1f} BPM")
        
        # Find time offset
        time_offset = find_time_offset(ref_audio, user_audio, sr)
        
        # Determine which video needs the offset
        if time_offset > 0:
            logger.info(f"Reference video should start {time_offset:.2f} seconds later")
            offset_video = "reference"
        else:
            logger.info(f"User video should start {abs(time_offset):.2f} seconds later")
            offset_video = "user"
        
        # Consider it the same song if tempo difference is small
        is_same_song = tempo_diff < 5.0
        
        logger.info(f"Same song detected: {is_same_song}")
        logger.info(f"Offset video: {offset_video}")
        
        return is_same_song, 1.0 if is_same_song else 0.0, time_offset, ref_beats, user_beats
    except Exception as e:
        logger.error(f"Error in compare_audio_similarity: {str(e)}")
        raise 