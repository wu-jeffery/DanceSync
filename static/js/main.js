document.addEventListener('DOMContentLoaded', () => {
    const referenceFile = document.getElementById('referenceFile');
    const userFile = document.getElementById('userFile');
    const referenceVideo = document.getElementById('referenceVideo');
    const userVideo = document.getElementById('userVideo');
    const compareBtn = document.getElementById('compareBtn');
    const results = document.getElementById('results');
    const videoContainer = document.getElementById('videoContainer');

    let referenceKeypoints = null;
    let userKeypoints = null;
    let referenceFilename = null;
    let userFilename = null;
    let originalReferenceFilename = null;
    let originalUserFilename = null;
    let timeOffset = 0;
    let isSynced = false;

    // Setup video synchronization with time offset
    function setupVideoSync() {
        if (referenceVideo.src && userVideo.src) {
            // Remove any existing event listeners
            referenceVideo.removeEventListener('play', syncPlay);
            referenceVideo.removeEventListener('pause', syncPause);
            referenceVideo.removeEventListener('seeked', syncSeek);
            referenceVideo.removeEventListener('ratechange', syncRate);
            userVideo.removeEventListener('play', syncPlay);
            userVideo.removeEventListener('pause', syncPause);
            userVideo.removeEventListener('seeked', syncSeek);
            userVideo.removeEventListener('ratechange', syncRate);

            // Reset videos to beginning
            referenceVideo.currentTime = 0;
            userVideo.currentTime = 0;

            // Apply time offset
            if (timeOffset > 0) {
                // Reference video needs to start later
                referenceVideo.currentTime = timeOffset;
            } else {
                // User video needs to start later
                userVideo.currentTime = Math.abs(timeOffset);
            }

            // Setup synchronized playback for both videos
            [referenceVideo, userVideo].forEach(video => {
                video.addEventListener('play', syncPlay);
                video.addEventListener('pause', syncPause);
                video.addEventListener('seeked', syncSeek);
                video.addEventListener('ratechange', syncRate);
            });

            // Add custom controls
            addCustomControls();

            // Log the current sync state
            console.log(`Video sync setup complete. Time offset: ${timeOffset}s`);
            console.log(`Reference video starts at: ${referenceVideo.currentTime}s`);
            console.log(`User video starts at: ${userVideo.currentTime}s`);
            
            isSynced = true;
        }
    }

    // Add custom video controls
    function addCustomControls() {
        // Create controls container
        const controls = document.createElement('div');
        controls.className = 'custom-controls';
        
        // Play/Pause button
        const playPauseBtn = document.createElement('button');
        playPauseBtn.innerHTML = '▶';
        playPauseBtn.onclick = () => {
            if (referenceVideo.paused) {
                referenceVideo.play();
            } else {
                referenceVideo.pause();
            }
        };
        
        // Time display
        const timeDisplay = document.createElement('span');
        timeDisplay.className = 'time-display';
        
        // Progress bar
        const progressBar = document.createElement('input');
        progressBar.type = 'range';
        progressBar.min = 0;
        progressBar.max = 100;
        progressBar.value = 0;
        progressBar.className = 'progress-bar';
        
        // Update time display and progress bar
        const updateTimeDisplay = () => {
            const currentTime = referenceVideo.currentTime;
            const duration = referenceVideo.duration;
            timeDisplay.textContent = `${formatTime(currentTime)} / ${formatTime(duration)}`;
            progressBar.value = (currentTime / duration) * 100;
        };
        
        // Format time in MM:SS format
        const formatTime = (seconds) => {
            const minutes = Math.floor(seconds / 60);
            seconds = Math.floor(seconds % 60);
            return `${minutes}:${seconds.toString().padStart(2, '0')}`;
        };
        
        // Add event listeners for time updates
        referenceVideo.addEventListener('timeupdate', updateTimeDisplay);
        
        // Handle progress bar changes
        progressBar.addEventListener('input', () => {
            const time = (progressBar.value / 100) * referenceVideo.duration;
            referenceVideo.currentTime = time;
        });
        
        // Add elements to controls
        controls.appendChild(playPauseBtn);
        controls.appendChild(timeDisplay);
        controls.appendChild(progressBar);
        
        // Add controls to video container
        videoContainer.appendChild(controls);
    }

    // Synchronization event handlers
    function syncPlay(event) {
        if (isSynced) {
            const sourceVideo = event.target;
            const otherVideo = sourceVideo === referenceVideo ? userVideo : referenceVideo;
            otherVideo.play();
        }
    }

    function syncPause(event) {
        if (isSynced) {
            const sourceVideo = event.target;
            const otherVideo = sourceVideo === referenceVideo ? userVideo : referenceVideo;
            otherVideo.pause();
        }
    }

    function syncSeek(event) {
        if (isSynced) {
            const sourceVideo = event.target;
            const otherVideo = sourceVideo === referenceVideo ? userVideo : referenceVideo;
            if (timeOffset > 0) {
                otherVideo.currentTime = sourceVideo.currentTime - timeOffset;
            } else {
                otherVideo.currentTime = sourceVideo.currentTime + Math.abs(timeOffset);
            }
        }
    }

    function syncRate(event) {
        if (isSynced) {
            const sourceVideo = event.target;
            const otherVideo = sourceVideo === referenceVideo ? userVideo : referenceVideo;
            otherVideo.playbackRate = sourceVideo.playbackRate;
        }
    }

    // Check if both videos are uploaded and sync them
    async function checkAndSyncVideos() {
        if (originalReferenceFilename && originalUserFilename) {
            try {
                results.innerHTML = '<div class="loading"></div> Synchronizing videos...';
                const response = await fetch('/sync_audio', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        reference_video: originalReferenceFilename,
                        user_video: originalUserFilename
                    })
                });

                const data = await response.json();
                if (response.ok) {
                    timeOffset = data.time_offset;
                    setupVideoSync();
                    results.innerHTML = `
                        <div class="sync-info">
                            <p>Videos synchronized!</p>
                            <p>Audio similarity: ${(data.audio_similarity * 100).toFixed(1)}%</p>
                            <p>Time offset: ${Math.abs(timeOffset).toFixed(2)} seconds</p>
                            <p>${timeOffset > 0 ? 'Reference video starts later' : 'User video starts later'}</p>
                            <p>Reference BPM: ${data.reference_tempo?.toFixed(1) || 'N/A'}</p>
                            <p>User BPM: ${data.user_tempo?.toFixed(1) || 'N/A'}</p>
                        </div>
                    `;
                    compareBtn.disabled = false;
                } else {
                    results.innerHTML = `Error: ${data.error || 'Failed to synchronize videos'}`;
                }
            } catch (error) {
                results.innerHTML = `Error synchronizing videos: ${error.message}`;
                console.error('Error:', error);
            }
        }
    }

    // Handle reference video upload
    referenceFile.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            const url = URL.createObjectURL(file);
            referenceVideo.src = url;
            
            // Upload to server
            const formData = new FormData();
            formData.append('video', file);
            
            try {
                results.innerHTML = '<div class="loading"></div> Processing reference video...';
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                if (response.ok) {
                    if (data.keypoints) {
                        referenceKeypoints = data.keypoints;
                        referenceFilename = data.filename;
                        originalReferenceFilename = data.original_filename;
                        
                        // Update video source to processed video
                        referenceVideo.src = `/uploads/${referenceFilename}`;
                        checkAndSyncVideos();
                    } else {
                        results.innerHTML = 'No poses detected in the video. Please try a different video.';
                    }
                } else {
                    results.innerHTML = `Error: ${data.error || 'Failed to process video'}`;
                }
            } catch (error) {
                results.innerHTML = `Error processing reference video: ${error.message}`;
                console.error('Error:', error);
            }
        }
    });

    // Handle user video upload
    userFile.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            const url = URL.createObjectURL(file);
            userVideo.src = url;
            
            // Upload to server
            const formData = new FormData();
            formData.append('video', file);
            
            try {
                results.innerHTML = '<div class="loading"></div> Processing your video...';
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                if (response.ok) {
                    if (data.keypoints) {
                        userKeypoints = data.keypoints;
                        userFilename = data.filename;
                        originalUserFilename = data.original_filename;
                        
                        // Update video source to processed video
                        userVideo.src = `/uploads/${userFilename}`;
                        checkAndSyncVideos();
                    } else {
                        results.innerHTML = 'No poses detected in the video. Please try a different video.';
                    }
                } else {
                    results.innerHTML = `Error: ${data.error || 'Failed to process video'}`;
                }
            } catch (error) {
                results.innerHTML = `Error processing your video: ${error.message}`;
                console.error('Error:', error);
            }
        }
    });

    // Handle comparison
    compareBtn.addEventListener('click', async () => {
        if (!referenceKeypoints || !userKeypoints) return;

        try {
            results.innerHTML = '<div class="loading"></div> Analyzing dances...';
            const response = await fetch('/compare', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    reference_keypoints: referenceKeypoints,
                    user_keypoints: userKeypoints,
                    reference_video: originalReferenceFilename,
                    user_video: originalUserFilename
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                displayComparisonResults(data.results, data.average_similarity, data.num_beats_analyzed);
            } else {
                results.innerHTML = `Error: ${data.error || 'Failed to compare dances'}`;
            }
        } catch (error) {
            results.innerHTML = 'Error comparing dances';
            console.error('Error:', error);
        }
    });

    // Display comparison results
    function displayComparisonResults(results, averageSimilarity, numBeatsAnalyzed) {
        let html = '<div class="comparison-results">';
        
        html += `
            <div class="overall-score">
                <h3>Analysis Complete</h3>
                <p>Overall Dance Similarity: ${(averageSimilarity * 100).toFixed(1)}%</p>
                <p>Number of beats analyzed: ${numBeatsAnalyzed}</p>
                <p>Use the controls below to play/pause both videos simultaneously.</p>
            </div>
        `;
        html += '</div>';
        
        results.innerHTML = html;
    }
}); 