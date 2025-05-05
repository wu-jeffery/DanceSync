document.addEventListener('DOMContentLoaded', () => {
    const referenceFile = document.getElementById('referenceFile');
    const userFile = document.getElementById('userFile');
    const referenceVideo = document.getElementById('referenceVideo');
    const userVideo = document.getElementById('userVideo');
    const referenceStream = document.getElementById('referenceStream');
    const userStream = document.getElementById('userStream');
    const compareBtn = document.getElementById('compareBtn');
    const results = document.getElementById('results');

    let referenceKeypoints = null;
    let userKeypoints = null;
    let referenceFilename = null;
    let userFilename = null;

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
                        updateCompareButton();
                        
                        // Show the processed video stream with keypoints
                        referenceVideo.classList.add('d-none');
                        referenceStream.classList.remove('d-none');
                        referenceStream.src = `/video_feed/${referenceFilename}`;
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
                        updateCompareButton();
                        
                        // Show the processed video stream with keypoints
                        userVideo.classList.add('d-none');
                        userStream.classList.remove('d-none');
                        userStream.src = `/video_feed/${userFilename}`;
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

    // Update compare button state
    function updateCompareButton() {
        compareBtn.disabled = !(referenceKeypoints && userKeypoints);
        if (!compareBtn.disabled) {
            results.innerHTML = 'Ready to compare! Click the Compare button to start.';
        }
    }

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
                    user_keypoints: userKeypoints
                })
            });

            const data = await response.json();
            displayComparisonResults(data.results);
        } catch (error) {
            results.innerHTML = 'Error comparing dances';
            console.error('Error:', error);
        }
    });

    // Display comparison results
    function displayComparisonResults(results) {
        let html = '<div class="comparison-results">';
        
        // Calculate average similarity
        const avgSimilarity = results.reduce((sum, r) => sum + r.similarity, 0) / results.length;
        
        html += `<div class="overall-score">
            <h3>Overall Similarity: ${(avgSimilarity * 100).toFixed(1)}%</h3>
        </div>`;
        
        // Display frame-by-frame comparison
        html += '<div class="frame-comparison">';
        results.forEach(result => {
            html += `
                <div class="comparison-frame">
                    <div class="frame-header">
                        <h4>Frame ${result.frame}</h4>
                        <span class="similarity-score">${(result.similarity * 100).toFixed(1)}%</span>
                    </div>
                    <div class="frame-images">
                        <div class="reference-frame">
                            <img src="/uploads/${result.reference_frame}" alt="Reference pose">
                            <p>Reference</p>
                        </div>
                        <div class="user-frame">
                            <img src="/uploads/${result.user_frame}" alt="User pose">
                            <p>Your Pose</p>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div></div>';
        
        results.innerHTML = html;
    }
}); 