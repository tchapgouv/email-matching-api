import os
import yaml
import re
import tempfile
import subprocess
import logging
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

config = None
pattern_to_platform = None

# Get environment variables
config_file = os.getenv('CONFIG_FILE', 'config.yaml')
repo_url = os.getenv('GIT_REPO_URL', 'https://github.com/tchapgouv/email-matching-api.git')
git_branch = os.getenv('GIT_BRANCH', 'main')
ssh_private_key = os.getenv('SSH_PRIVATE_KEY')

# Create a temporary file to hold the SSH private key
ssh_key_file = tempfile.NamedTemporaryFile(delete=False)
ssh_key_file.write(ssh_private_key.encode())
ssh_key_file.close()

def load_config():
    global config, pattern_to_platform

    logging.info("Loading configuration...")

    # Set the GIT_SSH_COMMAND environment variable to use the SSH key
    os.environ['GIT_SSH_COMMAND'] = f'ssh -i {ssh_key_file.name} -o StrictHostKeyChecking=no -F /dev/null'

    # Create a temporary directory to clone the repository
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Clone the repository with depth 1
        subprocess.run(["git", "clone", "-b", git_branch, "--depth", "1", repo_url, tmpdirname], check=True)

        # Load configuration from YAML file
        with open(os.path.join(tmpdirname, config_file)) as f:
            config = yaml.safe_load(f)

        # Prepare a dictionary to map each pattern to a platform
        pattern_to_platform = {}
        for pattern, platform in config['medium']['email']['patterns'].items():
            pattern_to_platform[re.compile(pattern)] = platform

    logging.info("Configuration loaded.")

# Call load_config at start
load_config()

@app.route('/_matrix/identity/api/v1/info')
def get_info():
    # Get email address from request parameters
    address = request.args.get('address', '')
    if not address:
        logging.error("No address provided")
        return jsonify({'error': 'No address provided'}), 400

    # Find the first pattern that matches the email address
    for pattern, platform in pattern_to_platform.items():
        if pattern.match(address):
            # If we found a match, return the corresponding platform
            logging.info(f"Match found for address {address}: {config['platforms'][platform]['hs']}")
            return jsonify({'hs': config['platforms'][platform]['hs']}), 200

    # If no match was found, return an error
    logging.error(f"No matching pattern found for address {address}")
    return jsonify({'error': 'No matching pattern found'}), 404

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    interval = int(os.getenv('INTERVAL', '24')) # default to 24 hours if INTERVAL is not set
    scheduler.add_job(func=load_config, trigger="interval", hours=interval)
    scheduler.start()
    port = int(os.getenv('PORT', 5000))  # Default port is 5000 if PORT environment variable is not set
    app.run(host='0.0.0.0', port=port)
