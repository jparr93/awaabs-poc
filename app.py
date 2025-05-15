from flask import Flask, render_template, request, redirect, url_for
from azure.servicebus import ServiceBusClient, ServiceBusMessage
import os
from dotenv import load_dotenv
from config.config import Config
from openaiproto import analyze_image
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Get configuration from environment variables
            endpoint = os.getenv("ENDPOINT_URL")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            deployment = os.getenv("DEPLOYMENT_NAME")
            
            # Analyze the image
            result = analyze_image(filepath, endpoint, api_key, deployment)
            
            # Clean up the uploaded file
            os.remove(filepath)
            
            # Send to Service Bus queue based on result
            if result and not result.startswith("Error"):
                connection_string = app.config['SERVICE_BUS_CONNECTION_STRING']
                with ServiceBusClient.from_connection_string(connection_string) as client:
                    queue_name = "urgent-cases" if "urgent request" in result.lower() else \
                               "standard-cases" if "standard request" in result.lower() else \
                               "no-mould-cases"
                    
                    with client.get_queue_sender(queue_name) as sender:
                        message = ServiceBusMessage(result)
                        sender.send_messages(message)
            
            return render_template('result.html', result=result)
    
    return render_template('index.html')

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
