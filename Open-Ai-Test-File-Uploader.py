import os
import base64
import json
import datetime
from openai import AzureOpenAI
from azure.servicebus import ServiceBusClient, ServiceBusMessage

# Azure OpenAI Configuration
endpoint = os.getenv("ENDPOINT_URL", "")
api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4.1")

# Azure Service Bus Configuration
servicebus_connection_string = os.getenv("SERVICE_BUS_CONNECTION_STRING", 
    "")
urgent_queue = os.getenv("URGENT_QUEUE_NAME", "urgent")
standard_queue = os.getenv("STANDARD_QUEUE_NAME", "standard")
no_mould_queue = os.getenv("NO_MOULD_QUEUE_NAME", "nomould")

def send_to_queue(message_content, queue_name, image_path):
    try:
        if not servicebus_connection_string:
            raise ValueError("Service Bus connection string is not set")
            
        # Create a payload with metadata
        payload = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "analysis_result": message_content,
            "image_path": image_path,
            "severity": queue_name
        }

        # Create Service Bus message
        message = ServiceBusMessage(json.dumps(payload))

        # Send message to queue
        with ServiceBusClient.from_connection_string(servicebus_connection_string) as client:
            with client.get_queue_sender(queue_name) as sender:
                sender.send_messages(message)
                print(f"Message sent to queue: {queue_name}")
    except Exception as e:
        print(f"Error sending to queue: {str(e)}")
        raise

def analyze_image_and_queue(image_path):
    # Initialize Azure OpenAI client
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2025-01-01-preview",
    )

    try:
        with open(image_path, 'rb') as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('ascii')
    except FileNotFoundError:
        print(f"Error: Could not find the image file at {image_path}")
        return
    except Exception as e:
        print(f"Error: {str(e)}")
        return

    chat_prompt = [
        {
            "role": "system",
            "content": """I want you to act as a mould detector in a home. You must only reply to requests that contains images. 
            \n\nYou must evaluate the image and determine whether the picture has mould in it and which room the mould is located in.
            \n\nIf mould is detected and is in a bedroom, you need to output that this is an urgent request. All other images with mould in, should output as a standard request.
            \n\nIf no mould is detected, you should output that no mould was detected in the image.
            \n\nIf extensive mould is detected but it isn't in a bedroom you should output that this is an urgent request."""
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{encoded_image}"
                    }
                },
                {
                    "type": "text",
                    "text": "Is there any mould in this image?"
                }
            ]
        }
    ]

    messages = chat_prompt

    try:
        completion = client.chat.completions.create(
            model=deployment,
            messages=messages,
            max_tokens=800,
            temperature=1,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            stream=False
        )
        
        result = completion.choices[0].message.content
        print(f"Analysis result: {result}")

        # Determine which queue to use based on the content
        if "urgent request" in result.lower():
            queue_name = urgent_queue
        elif "standard request" in result.lower():
            queue_name = standard_queue
        else:
            queue_name = no_mould_queue

        # Send to appropriate queue with image path
        send_to_queue(result, queue_name, image_path)

    except Exception as e:
        print(f"Error in analysis: {str(e)}")

def get_image_path():
    """Prompt user for image path or use default"""
    default_path = r"C:\Users\Joe\Downloads\FE\mould-on-wall-213x300.jpg"
    
    print("\nMould Detection Image Upload")
    print("-" * 30)
    print(f"Default image path: {default_path}")
    user_input = input("Enter image path (or press Enter for default): ").strip()
    
    return user_input if user_input else default_path

def validate_image_path(image_path):
    """Validate if the image path exists and is a supported format"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    supported_formats = {'.jpg', '.jpeg', '.png'}
    file_ext = os.path.splitext(image_path)[1].lower()
    
    if file_ext not in supported_formats:
        raise ValueError(f"Unsupported image format. Supported formats: {', '.join(supported_formats)}")
    
    return True

if __name__ == "__main__":
    try:
        # Get image path from user
        image_path = get_image_path()
        
        # Validate image path
        validate_image_path(image_path)
        
        print(f"\nProcessing image: {image_path}")
        analyze_image_and_queue(image_path)
        
    except (FileNotFoundError, ValueError) as e:
        print(f"\nError: {str(e)}")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")