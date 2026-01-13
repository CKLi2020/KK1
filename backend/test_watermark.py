
import os
import sys
print("Starting test_watermark.py...")
from PIL import Image, ImageDraw

# Add current directory to path so we can import user_service
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from user_service import add_watermark_to_image

def test_watermark():
    # Create a dummy white image
    width, height = 800, 1000
    image = Image.new('RGB', (width, height), (255, 255, 255))
    
    # Add some text to the background to make it look like a document
    draw = ImageDraw.Draw(image)
    for i in range(0, height, 50):
        draw.line([(0, i), (width, i)], fill='red', width=1)
    
    print("Created dummy image.")
    
    # Apply watermark
    print("Applying watermark...")
    watermarked = add_watermark_to_image(image, "一纸相思")
    
    # Save output
    output_path = "test_watermark_output.png"
    watermarked.save(output_path)
    print(f"Saved watermarked image to {output_path}")

if __name__ == "__main__":
    test_watermark()
