// Get elements
const uploadButton = document.getElementById('uploadButton');
const fileInput = document.getElementById('fileInput');
const recordButtonText = document.getElementById('recordButtonText');
const transcriptionText = document.getElementById('transcriptionText');
const summaryText = document.getElementById('summaryText');

function redirectTo(url) {
    window.location.href = url;
}

// Trigger the file input dialog when the upload button is clicked
uploadButton.addEventListener('click', () => fileInput.click());

// Handle file selection and upload
fileInput.addEventListener('change', () => {
    const file = fileInput.files[0];
    if (file) {
        const formData = new FormData();
        formData.append('audio', file); // Changed 'file' to 'audio' to match Flask

        // Send the file to the server using fetch
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            transcriptionText.innerText = `Transcribed Text: ${data.transcription || 'Transcription coming soon...'}`;
            summaryText.innerText = `Summary: ${data.summary || 'Summary coming soon...'}`;
        })
        .catch(error => {
            alert('Error uploading file!');
            console.error('Error:', error);
        });
    }
});
