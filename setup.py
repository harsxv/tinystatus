from pathlib import Path
import shutil

def setup_project():
    # Create necessary directories
    Path("app/static/assets").mkdir(parents=True, exist_ok=True)
    Path("app/templates").mkdir(parents=True, exist_ok=True)
    
    # Copy assets
    if Path("assets").exists():
        shutil.copytree("assets", "app/static/assets", dirs_exist_ok=True)
    
    # Copy template files
    if Path("index.html.theme").exists():
        shutil.copy("index.html.theme", "app/templates/")
        
    if Path("history.html.theme").exists():
        shutil.copy("history.html.theme", "app/templates/")
        
    

if __name__ == "__main__":
    setup_project() 