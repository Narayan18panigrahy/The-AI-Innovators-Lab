import os
import random
import time
from datetime import datetime, timedelta
import subprocess
from groq import Groq
import logging
from typing import Dict, Optional

# --- Configuration ---
AUTHORS = {
    "you": {"name": "Rohit Ranjan", "email": "29282712+Itzsrohit@users.noreply.github.com"},
    "friend": {"name": "Narayan Panigrahy", "email": "18panigrahy@users.noreply.github.com"}
}

# --- File Processing Rules ---
SCRIPT_NAME = os.path.basename(__file__)
INCLUDE_EXTENSIONS = {'.py', '.js', '.html', '.css', '.md', '.txt'}
EXCLUDE_PATTERNS = {'.git', 'node_modules', 'venv', '__pycache__', '.env', SCRIPT_NAME}

# --- History Simulation Parameters ---
MAX_COMMIT_LENGTH = 72
CHUNK_SIZE = {
    '.py': 100,      # Smaller chunks for code
    '.js': 170, 
    '.html': 190,    # Larger chunks for markup
    '.css': 180,
    '.md': 250,      # Very large for docs
    '.txt': 250,
    'default': 130    # Fallback
}
MAX_TOKENS = 60
CODE_CONTEXT_LIMIT = 800  # Characters sent to LLM

# --- Time Simulation ---
SIMULATION_RANGE_DAYS = 90
WEEKEND_COMMIT_RATIO = 0.7
WORKDAY_NIGHT_START = 19
WORKDAY_END = 23

# --- Groq API ---
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_REQUESTS_PER_MINUTE = 30
SAFETY_BUFFER = 5  # Process 25 RPM

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('git_history.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TokenTracker:
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
    
    def add_usage(self, prompt: str, response) -> None:
        self.input_tokens += len(prompt.split())  # Approximate
        if hasattr(response, 'usage'):
            self.output_tokens += response.usage.completion_tokens

token_tracker = TokenTracker()
last_request_time = 0

# --- File Handling Functions ---
def read_file_safely(path: str) -> Optional[str]:
    """Read files with UTF-8 encoding, skip unreadable files"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Skipping {path} (error: {str(e)})")
        return None

def write_file_safely(path: str, content: str) -> None:
    """Write files with UTF-8 encoding"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def should_include_file(file_path: str) -> bool:
    """Check if file should be processed"""
    if any(pattern.lower() in file_path.lower() for pattern in EXCLUDE_PATTERNS):
        return False
    return any(file_path.lower().endswith(ext) for ext in INCLUDE_EXTENSIONS)

# --- Chunk Processing ---
def generate_chunks(content: str, chunk_size: int):
    """Split content into logical chunks with Windows/Unix line ending awareness"""
    lines = content.replace('\r\n', '\n').split('\n')
    for i in range(0, len(lines), chunk_size):
        yield '\n'.join(lines[i:i + chunk_size])

def get_chunk_size(file_path: str) -> int:
    """Dynamic chunk sizing based on file type"""
    ext = os.path.splitext(file_path)[1].lower()
    return CHUNK_SIZE.get(ext, CHUNK_SIZE['default'])

# --- Commit Generation ---
def make_commit(file_path: str, chunk: str, author: str, date: datetime) -> bool:
    """Create a commit with proper metadata"""
    try:
        # Stage changes
        subprocess.run(['git', 'add', file_path], check=True, capture_output=True)
        
        # Generate message
        message = generate_commit_message(file_path, chunk)
        
        # Set commit environment
        date_str = date.strftime("%Y-%m-%d %H:%M:%S")
        env = {
            **os.environ,
            "GIT_AUTHOR_DATE": date_str,
            "GIT_COMMITTER_DATE": date_str
        }
        
        # Execute commit
        subprocess.run(
            ['git', 'commit', '-m', message,
             '--author', f"{AUTHORS[author]['name']} <{AUTHORS[author]['email']}>"],
            env=env,
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Commit failed for {file_path}: {e.stderr.decode().strip()}")
        return False

def generate_realistic_date() -> datetime:
    """Generate commit dates with realistic patterns"""
    base_date = datetime.now() - timedelta(days=random.randint(0, SIMULATION_RANGE_DAYS))
    
    if random.random() < WEEKEND_COMMIT_RATIO:  # Weekend
        return base_date.replace(
            hour=random.randint(10, 18),  # 10AM-6PM
            minute=random.randint(0, 59),
            second=0
        )
    else:  # Weekday night
        return base_date.replace(
            hour=random.randint(WORKDAY_NIGHT_START, WORKDAY_END),
            minute=random.randint(0, 59),
            second=0
        )

def generate_commit_message(file_path: str, code_chunk: str) -> str:
    """Generate technically precise commit messages"""
    global last_request_time
    
    prompt = f"""STRICTLY OUTPUT ONLY THE COMMIT MESSAGE IN THIS FORMAT:
    <type>(<scope>): <description>

    Where:
    - type: fix|feat|docs|style|refactor|test|chore
    - scope: filename or component
    - description: Specific technical change under 72 chars

    Example: 
    feat(auth): Add JWT login handler

    For changes to {file_path}:
    Code diff:
    ```{code_chunk[:CODE_CONTEXT_LIMIT]}```"""
    
    try:
        # Rate limiting
        elapsed = time.time() - last_request_time
        if elapsed < (60 / (MAX_REQUESTS_PER_MINUTE - SAFETY_BUFFER)):
            time.sleep(max(0, (60 / (MAX_REQUESTS_PER_MINUTE - SAFETY_BUFFER)) - elapsed))
        
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=MAX_TOKENS,
            temperature=0.2,
            stop=["\n"]
        )
        last_request_time = time.time()
        token_tracker.add_usage(prompt, response)
        
        # Clean and validate
        raw_msg = response.choices[0].message.content.strip()
        logger.info(f"raw msg = {raw_msg}")
        clean_msg = raw_msg.split('\n')[0].strip('"\'').strip()
        
        # Enforce conventional commits
        if not any(clean_msg.startswith(prefix) for prefix in 
                  ("feat(", "fix(", "refactor(", "docs(", "chore(", "test(", "style(")):
            clean_msg = f"chore({os.path.basename(file_path)}): {clean_msg[:30]}"
            
        return clean_msg[:MAX_COMMIT_LENGTH]
    
    except Exception as e:
        logger.warning(f"LLM failed: {e}")
        return f"chore({os.path.basename(file_path)}): Update file"

# --- Core Execution ---
def initialize_git() -> None:
    """Safe Git initialization without destructive cleanup"""
    if not os.path.exists('.git'):
        subprocess.run(['git', 'init'], check=True)
    
    # Stage everything to start clean
    subprocess.run(['git', 'add', '.'], 
                  stdout=subprocess.DEVNULL, 
                  stderr=subprocess.DEVNULL)
    
    # Initial commit if needed
    try:
        subprocess.run(['git', 'commit', '-m', "Initial repository setup"],
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL,
                      check=True)
    except subprocess.CalledProcessError:
        pass  # No files to commit is okay

def process_file(file_path: str) -> None:
    """Process a single file with proper chunking"""
    content = read_file_safely(file_path)
    if not content:
        return
        
    chunk_size = get_chunk_size(file_path)
    original_content = content
    
    for chunk in generate_chunks(content, chunk_size):
        if not chunk.strip():
            continue
            
        author = random.choice(list(AUTHORS.keys()))
        commit_date = generate_realistic_date()
        
        # Write chunk and commit
        write_file_safely(file_path, chunk)
        if make_commit(file_path, chunk, author, commit_date):
            logger.info(f"Committed changes to {file_path}")
        
    # Restore original
    write_file_safely(file_path, original_content)
    subprocess.run(['git', 'add', file_path], check=True)

def main() -> None:
    """Main execution flow"""
    logger.info("Starting Git history generation")
    initialize_git()
    
    try:
        for root, dirs, files in os.walk('.'):
            # Filter directories
            dirs[:] = [d for d in dirs if not any(
                pattern.lower() in os.path.join(root, d).lower()
                for pattern in EXCLUDE_PATTERNS
            )]
            
            for file in files:
                file_path = os.path.join(root, file)
                if should_include_file(file_path):
                    process_file(file_path)
                    
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
    finally:
        logger.info(f"Token usage: Input={token_tracker.input_tokens}, Output={token_tracker.output_tokens}")
        logger.info("History generation complete")

if __name__ == '__main__':
    try:
        GROQ_API_KEY = "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"
        client = Groq(api_key=GROQ_API_KEY or os.environ.get("GROQ_API_KEY"))
        if not client:
            raise ValueError("Groq API key not found in environment variables")
        main()
    except Exception as e:
        logger.critical(f"Initialization failed: {e}")