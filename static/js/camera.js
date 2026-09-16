let videoStream = null;
const video = document.getElementById('webcam');
const canvas = document.getElementById('capturedCanvas');
const btnStart = document.getElementById('btnStartCamera');
const btnCapture = document.getElementById('btnCapture');
const btnRetake = document.getElementById('btnRetake');
const webcamInput = document.getElementById('webcamInput');

if (btnStart) {
    btnStart.addEventListener('click', async () => {
        try {
            videoStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
            video.srcObject = videoStream;
            btnStart.classList.add('d-none');
            btnCapture.classList.remove('d-none');
        } catch (err) {
            alert("Camera access denied or no webcam available: " + err.message);
        }
    });

    btnCapture.addEventListener('click', () => {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

        webcamInput.value = canvas.toDataURL('image/jpeg');
        video.classList.add('d-none');
        canvas.classList.remove('d-none');
        btnCapture.classList.add('d-none');
        btnRetake.classList.remove('d-none');

        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
        }
    });

    btnRetake.addEventListener('click', async () => {
        webcamInput.value = "";
        canvas.classList.add('d-none');
        video.classList.remove('d-none');
        btnRetake.classList.add('d-none');
        btnCapture.classList.remove('d-none');

        videoStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
        video.srcObject = videoStream;
    });
}