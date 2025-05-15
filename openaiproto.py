import os
import base64
from openai import AzureOpenAI

def analyze_image(image_path, endpoint, api_key, deployment):
    # Initialize Azure OpenAI client with API key
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2025-01-01-preview",
    )

    try:
        with open(image_path, 'rb') as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('ascii')
    except FileNotFoundError:
        return "Error: Could not find the image file"
    except Exception as e:
        return f"Error: {str(e)}"

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

    try:
        completion = client.chat.completions.create(
            model=deployment,
            messages=chat_prompt,
            max_tokens=800,
            temperature=1,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            stream=False
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error in analysis: {str(e)}"

# Set your Azure OpenAI configuration
endpoint = os.getenv("ENDPOINT_URL", "https://ai-joeparr6466ai088487706282.openai.azure.com/")
api_key = os.getenv("AZURE_OPENAI_API_KEY", "Fq5U59rHptm3eT1LA8kRzAYk21YYIz3rNf5qsSTuCJ3j58OH01BdJQQJ99BBACYeBjFXJ3w3AAAAACOGpTIP")  # Make sure to set this environment variable
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4.1")

# Specify the path to your image using proper path formatting
IMAGE_PATH = r"C:\Users\Joe\Downloads\FE\mould-on-wall-213x300.jpg"  # Using raw string

result = analyze_image(IMAGE_PATH, endpoint, api_key, deployment)
print(result)