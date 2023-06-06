# Email Matching API

The Email Matching API is a Flask application that responds to API calls and matches email addresses with patterns specified in a configuration file. The configuration file is loaded from a git repository at launch and refreshed at a regular interval.

## Env vars

```
export REPO_URL='https://github.com/yourgithubusername/config-repo.git'
export SSH_PRIVATE_KEY='-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----'
export CONFIG_FILE='config.yaml'
export GIT_BRANCH='master'
export INTERVAL='24'
export PORT='5000'
```
Note: INTERVAL is the number of hours between each refresh of the configuration file. PORT is the port number on which the Flask application will listen.

## Request
Make a GET request to http://localhost:5000/_matrix/identity/api/v1/info with a address query parameter containing the email address to be matched.

Example:

`
http://localhost:5000/_matrix/identity/api/v1/info?address=john.doe@beta.gouv.fr`
The API will return a JSON object containing the hs value associated with the matching pattern for the email address. If no matching pattern is found, an error message is returned.

## Troubleshooting
In case of issues, check the following:

- Ensure that all environment variables are set correctly.
- Make sure the SSH private key has the necessary permissions to access the git repository containing the configuration file.
- Verify that the configuration file and the git branch specified exist in the git repository.