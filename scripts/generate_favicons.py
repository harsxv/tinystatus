from PIL import Image
import os

def generate_favicons(source_image_path, output_dir):
    """Generate all required favicon and app icon files from a source image."""
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Open source image
    img = Image.open(source_image_path)
    
    # Ensure image is square
    size = min(img.size)
    if img.size != (size, size):
        img = img.crop((0, 0, size, size))
    
    # Generate various sizes for apple-touch-icon
    apple_sizes = [57, 60, 72, 76, 114, 120, 144, 152, 180]
    for size in apple_sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(os.path.join(output_dir, f'apple-icon-{size}x{size}.png'))
    
    # Generate android chrome icons
    android_sizes = [192, 384]
    for size in android_sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(os.path.join(output_dir, f'android-icon-{size}x{size}.png'))
    
    # Generate favicon sizes
    favicon_sizes = [16, 32, 96]
    favicon_images = []
    for size in favicon_sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(os.path.join(output_dir, f'favicon-{size}x{size}.png'))
        favicon_images.append(resized)
    
    # Generate favicon.ico (contains multiple sizes)
    favicon_images[0].save(
        os.path.join(output_dir, 'favicon.ico'),
        format='ICO',
        sizes=[(16, 16), (32, 32)]
    )
    
    # Generate mstile image
    mstile = img.resize((150, 150), Image.Resampling.LANCZOS)
    mstile.save(os.path.join(output_dir, 'ms-icon-150x150.png'))
    
    # Generate browserconfig.xml
    browserconfig = '''<?xml version="1.0" encoding="utf-8"?>
    <browserconfig>
        <msapplication>
            <tile>
                <square150x150logo src="/assets/ms-icon-150x150.png"/>
                <TileColor>#ffffff</TileColor>
            </tile>
        </msapplication>
    </browserconfig>'''
    
    with open(os.path.join(output_dir, 'browserconfig.xml'), 'w') as f:
        f.write(browserconfig)
    
    # Generate manifest.json
    manifest = '''{
        "name": "StatusWatch",
        "short_name": "StatusWatch",
        "icons": [
            {
                "src": "/assets/android-icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/assets/android-icon-384x384.png",
                "sizes": "384x384",
                "type": "image/png"
            }
        ],
        "theme_color": "#ffffff",
        "background_color": "#ffffff",
        "display": "standalone"
    }'''
    
    with open(os.path.join(output_dir, 'manifest.json'), 'w') as f:
        f.write(manifest)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python generate_favicons.py <source_image_path>")
        sys.exit(1)
    
    source_image = sys.argv[1]
    output_directory = "app/static/assets"
    
    generate_favicons(source_image, output_directory)
    print(f"Generated favicon files in {output_directory}")