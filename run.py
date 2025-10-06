import base64
import requests
import json
import os
import time
import random
import pdb
import argparse

# Your API key. Replace "YOUR_API_KEY" with your actual key.
# You can get a key from Google AI Studio at https://aistudio.google.com/app/apikey
# It's recommended to store this in an environment variable for security.
API_KEY = "AIzaSyCGLRPfgrgzWDURKHfFNHpUctTcAONmWuE"

# API_KEY = os.environ.get("API_KEY")
# if API_KEY:
#     # Use the API key
#     print("API Key loaded successfully!")
# else:
#     print("API Key not found.")

# pdb.set_trace()
# The Gemini model for image generation and editing
MODEL_ID = "gemini-2.5-flash-image-preview"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={API_KEY}"

def encode_image_to_base64(image_path):
    """
    Encodes a local image file to a base64 string.
    This is required for sending the image data to the API.
    """
    if not os.path.exists(image_path):
        print(f"Error: The image file '{image_path}' was not found.")
        return None
    
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string

def edit_image_with_gemini(image_path, prompt_text, output_path="edited_image.jpg"):
    """
    Sends an image and a text prompt to the Gemini API for editing.

    Args:
        image_path (str): The local path to the image to be edited.
        prompt_text (str): The text prompt describing the desired edit.
        output_path (str): The path to save the edited image.
    """
    print("Preparing image and prompt for the API...")

    # Encode the image to base64
    image_base64 = encode_image_to_base64(image_path)
    if not image_base64:
        return

    # Create the payload for the API request
    payload = {
        "contents": [{
            "parts": [
                {
                    "text": prompt_text
                },
                {
                    "inlineData": {
                        "mimeType": "image/jpeg",  # Using jpeg to match the .jpg file extension
                        "data": image_base64
                    }
                }
            ]
        }],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "temperature": 0.1
        }
    }

    headers = {
        "Content-Type": "application/json"
    }
    
    # Retry logic with exponential backoff
    retries = 0
    max_retries = 5
    wait_time = 10  # Initial wait time in seconds

    while retries < max_retries:
        print(f"Attempting to send request... (Attempt {retries + 1}/{max_retries})")
        try:
            response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()  # Raise an exception for bad status codes
            
            result = response.json()
            
            # Extract the edited image data
            edited_image_data = None
            for candidate in result.get("candidates", []):
                for part in candidate.get("content", {}).get("parts", []):
                    if "inlineData" in part:
                        edited_image_data = part["inlineData"]["data"]
                        break
                if edited_image_data:
                    break
            
            if edited_image_data:
                print("Successfully received edited image data. Decoding and saving...")
                # Decode the base64 data and save the image
                decoded_image = base64.b64decode(edited_image_data)
                with open(output_path, "wb") as f:
                    f.write(decoded_image)
                print(f"Edited image saved successfully to '{output_path}'")
                return  # Exit the function on success
            else:
                print("No image data found in the API response.")
                print(json.dumps(result, indent=2))
                return 
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                retries += 1
                print(f"HTTP Error 429: Quota exceeded. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                wait_time *= 2  # Exponential backoff
            else:
                print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
                return
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return
            
    print(f"Failed to get a successful response after {max_retries} attempts. Please try again later or check your quota.")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Generate images with pedestrians and bicycles using Gemini API")
    parser.add_argument("--input_image", "-i", type=str, default="background_images/CAM3.png", 
                        help="Path to the input image (default: background_images/CAM3.png)")
    parser.add_argument("--dest_folder", "-d", type=str, 
                        default="output/CAM3_ped_bic/images",
                        help="Destination folder for generated images")
    parser.add_argument("--num_images", "-n", type=int, default=100,
                        help="Number of images to generate (default: 100)")
    
    args = parser.parse_args()
    
    # --- Configuration ---
    input_image_path = args.input_image
    dest_folder = args.dest_folder
    num_images_to_generate = args.num_images

    # Base name for output files
    base_output_name = "generated_CAM3_pedestrian_bicycle"
    output_extension = ".png"

    print(f"Starting to generate {num_images_to_generate} images...")
    print(f"Input image: {input_image_path}")
    print(f"Destination folder: {dest_folder}")

    # Destination folder for generated images
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    for i in range(num_images_to_generate):
        # Dynamically generate the prompt for each iteration for greater variety
        #num_cars = random.randint(0, 3)
        #num_trucks = random.randint(2, 6)
        #num_motorcycles = random.randint(10, 15)
        #num_buses = random.randint(3, 7)
        num_bicycles = random.randint(5, 10)
        num_pedestrians = random.randint(7, 12)
        editing_prompt = (
            f"I have an imbalanced dataset and I need more images with pedestrians, and bicycles. "
            f"Please add {num_pedestrians} pedestrians, and {num_bicycles} bicycles to this street scene."
            f"Ensure the objects are proportionate to the scene and blend naturally with the environment. "
            f"Make sure that the pedestrians are walking on the sidewalks and crossing at crosswalks."
            f"Make sure that the bicycles are on the road and in bike lanes where available."
            f"Make sure that the bicycles are driven by people wearing helmets."
            f"Make sure that the objects that are far away are smaller in size to maintain perspective."
            f"Also, include a few cars to maintain realism. The total number of vehicles should create a realistic traffic scene."
        )

        rand_num = random.randint(1000, 9999)
        current_output_path = f"{base_output_name}_{i+1}_{rand_num}{output_extension}"
        print(f"\n--- Generating image {i+1}/{num_images_to_generate} ---")
        print(f"Using prompt: {editing_prompt}")
        print(f"Output path for this image: {current_output_path}")

        edit_image_with_gemini(input_image_path, editing_prompt, current_output_path)

        # Move the generated image to the destination folder
        dest_path = os.path.join(dest_folder, os.path.basename(current_output_path))
        try:
            os.rename(current_output_path, dest_path)
            print(f"Moved generated image to {dest_path}")
        except Exception as e:
            print(f"Failed to move image: {e}")

        # Add a small delay between requests to be kinder to rate limits
        if i < num_images_to_generate - 1:
            time.sleep(2)
    
    print("\nFinished generating images!")



