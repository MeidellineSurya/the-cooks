import sqlite3
from Flask import Flask, request, jsonify
from google.cloud import speech_v1p1beta1 as speech
from transformers import pipeline

app = Flask(__name__)

def setup_database():
    # Establish a connection to the database (or create it if it doesn't exist)
    conn = sqlite3.connect('savior.db')
    cursor = conn.cursor()

    # Define SQL command to create a 'transcriptions' table
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS transcriptions (
        id INTEGER PRIMARY KEY,
        video_url TEXT UNIQUE,
        transcription TEXT,
        summary TEXT
    )
    '''

    # Execute the SQL command
    cursor.execute(create_table_sql)

    # Commit the transaction to save changes
    conn.commit()

    # Close the cursor
    cursor.close()

    return conn

def transcribe_and_summarize(video_url, conn):
    # Initialize Google Cloud Speech-to-Text client
    client = speech.SpeechClient()

    # Set up the audio file for transcription
    audio_config = speech.RecognitionAudio(uri=video_url)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="en-US",
    )

    # Perform the transcription
    response = client.recognize(config=config, audio=audio_config)

    # Extract the transcription from the response
    transcription = ""
    for result in response.results:
        transcription += result.alternatives[0].transcript

    # Summarize the transcription
    summarizer = pipeline("summarization")
    summary = summarizer(transcription, max_length=150, min_length=30, do_sample=False)[0]['summary_text']

    # Insert data into the 'transcriptions' table
    cursor = conn.cursor()
    insert_data_sql = '''
    INSERT INTO transcriptions (video_url, transcription, summary) VALUES (?, ?, ?)
    '''
    trans_data = (video_url, transcription, summary)
    cursor.execute(insert_data_sql, trans_data)
    conn.commit()
    cursor.close()

    return transcription, summary

@app.route('/save_credentials', methods=['POST'])
def save_credentials():
    data = request.json
    username = data['username']
    password = data['password']
    
    # Here, you would save the username and password into your database
    # Example:
    # cursor = conn.cursor()
    # cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    # conn.commit()
    
    return jsonify({'message': 'Credentials saved successfully'})

@app.route('/submit_video_url', methods=['POST'])
def submit_video_url():
    data = request.json
    video_url = data['video_url']
    
    # Transcribe audio from the video URL and summarize it
    transcription, summary = transcribe_and_summarize(video_url, conn)
    
    return jsonify({'message': 'Video URL submitted successfully'})

@app.route('/get_summary', methods=['GET'])
def get_summary():
    # Retrieve summary for the specified video URL
    video_url = request.args.get('video_url')
    
    cursor = conn.cursor()
    cursor.execute("SELECT summary FROM transcriptions WHERE video_url = ?", (video_url,))
    summary = cursor.fetchone()
    cursor.close()
    
    return jsonify({'summary': summary[0]}) if summary else jsonify({'message': 'Summary not found'})

if __name__ == "__main__":
    # Setup the database
    conn = setup_database()
    app.run(debug=True)
