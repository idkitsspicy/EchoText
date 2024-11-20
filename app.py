from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import wave
import json
from vosk import Model, KaldiRecognizer
import os
from dotenv import load_dotenv  # Import dotenv to load environment variables


# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')  # Use SECRET_KEY from .env or default

# Configure MongoDB using MongoDB Atlas URI from .env
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['flask_app']
users_collection = db['users']


# Configure file upload
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Vosk and Hugging Face configuration for audio processing
model_path = os.path.join(os.path.dirname(__file__), 'vosk-model-small-en-us-0.15')
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HF_API_KEY = os.getenv('HF_API_KEY')  # Use Hugging Face API key from .env

# Load Vosk model
if not os.path.exists(model_path):
    print("Model not found! Make sure you've downloaded and extracted it.")
    exit(1)
model = Model(model_path)
print("Model loaded successfully.")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Retrieve form data
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Check if the user already exists
        existing_user = users_collection.find_one({'username': username})
        if existing_user:
            flash('Username already exists, please choose a different one')
            return redirect(url_for('signup'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Insert user into the MongoDB collection
        users_collection.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password
        })

        flash('Signup successful, please log in')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Retrieve form data
        username = request.form['username']
        password = request.form['password']

        # Find the user in the MongoDB collection
        user = users_collection.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            # If the password is correct, start a user session
            session['username'] = username
            flash('Login successful')
            return redirect(url_for('dashboard'))

        flash('Invalid username or password')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out')
    return redirect(url_for('home'))

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        username = session['username']
        return render_template('dashboard.html')
    else:
        flash('You are not logged in')
        return redirect(url_for('login'))

# Audio upload, transcription, and summarization route
@app.route('/upload', methods=['POST'])
def upload():
    if 'username' in session:
        # Check if file part is in the request
        if 'audio' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['audio']
        
        if file.filename == '' or not allowed_file(file.filename):
            flash('Invalid file')
            return redirect(request.url)
        
        # Save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process the audio file for transcription
        transcribed_text = transcribe_audio(file_path)
        
        # Summarize the transcribed text
        summarized_text = summarize_text(transcribed_text)
        
        return jsonify({
            'message': 'Audio processed successfully',
            'transcription': transcribed_text,
            'summary': summarized_text
        })
    else:
        flash('You are not logged in')
        return redirect(url_for('login'))

def transcribe_audio(file_path):
    """ Transcribe audio file to text using Vosk model. """
    audio_file = wave.open(file_path, "rb")
    if (audio_file.getnchannels() != 1 or audio_file.getsampwidth() != 2 or 
        not(8000 <= audio_file.getframerate() <= 48000)):
        return "Error: Audio file must be WAV format mono PCM."

    recognizer = KaldiRecognizer(model, audio_file.getframerate())
    transcribed_text = ""
    while True:
        data = audio_file.readframes(4000)
        if len(data) == 0:
            break
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            transcribed_text += result['text'] + " "

    final_result = json.loads(recognizer.FinalResult())
    transcribed_text += final_result['text']
    audio_file.close()
    return transcribed_text

def summarize_text(text):
    """ Summarize text using Hugging Face API. """    

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": text}
    response = requests.post(HF_API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()[0]['summary_text']
    else:
        return "Error:Unable to summarize text"


if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
