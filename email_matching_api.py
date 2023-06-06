from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
import yaml
import os
import re
import tempfile
from git import Repo, Git
import subprocess

app = Flask(__name__)
pattern_to_platform = {}

# Create a temporary file for the SSH key
ssh_key_file = tempfile.NamedTemporaryFile(delete=False)
ssh_key_file.write(os.getenv('SSH_PRIVATE_KEY').encode())
ssh_key_file.close()

# Function to load config from the git repository
def load_config():
    global pattern_to_platform
    repo_url = os.getenv('REPO_URL')
    config_file = os.getenv('CONFIG_FILE', 'config.yaml')
    git_branch = os.getenv('GIT_BRANCH', 'master')

    # Setup git ssh command with private key
    git_ssh_cmd = f'ssh -i {ssh_key_file.name}'

    # Use a temporary directory to hold the configuration file
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Set GIT_SSH_COMMAND with custom ssh command
        with Git().custom_environment(GIT_SSH_COMMAND=git_ssh_cmd):
            # Pull only the required file from the repository
            subprocess.run(["git", "init"], cwd=tmpdirname, check=True)
            subprocess.run(["git", "config", "--local", "core.sparseCheckout", "true"], cwd=tmpdirname, check=True)
            with open(os.path.join(tmpdirname, ".git/info/sparse-checkout"), "w") as f:
                f.write(config_file + "\n")
            subprocess.run(["git", "remote", "add", "-f", "origin", repo_url], cwd=tmpdirname, check=True)
            subprocess.run(["git", "pull", "origin", git_branch], cwd=tmpdirname, check=True)
            # Load configuration from YAML file
            with open(os.path.join(tmpdirname, config_file)) as f:
                config = yaml.safe_load(f)

        # Prepare a dictionary to map each pattern to a platform
        pattern_to_platform = {}
        for pattern, platform in config['medium']['email']['patterns'].items():
            pattern_to_platform[re.compile(pattern)] = platform

    # Remove the temporary SSH key file
    os.unlink(ssh_key_file.name)

# Call load_config at start
load_config()

@app.route('/_matrix/identity/api/v1/info')
def get_info():
    # Get email address from request parameters
    address = request.args.get('address', '')
    if not address:
        return jsonify({'error': 'No address provided'}), 400

    # Find the first pattern that matches the email address
    for pattern, platform in pattern_to_platform.items():
        if pattern.match(address):
            # If we found a match, return the corresponding platform
            return jsonify({'hs': config['platforms'][platform]['hs']}), 200

    # If no match was found, return an error
    return jsonify({'error': 'No matching pattern found'}), 404

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    interval = int(os.getenv('INTERVAL', '24')) # default to 24 hours if INTERVAL is not set
    scheduler.add_job(func=load_config, trigger="interval", hours=interval)
    scheduler.start()
    app.run(debug=True, port=int(os.getenv('PORT', 5000)))
