import requests
import json
from typing import Dict
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Sample GitHub and Azure OpenAI configuration
GITHUB_REPO_OWNER = 'jktarun-apps'         # e.g., 'octocat'
GITHUB_REPO_NAME = 'SampleWeb'           # e.g., 'hello-world'
GITHUB_PR_NUMBER = os.getenv('GITHUB_PR_NUMBER') #1                       # e.g., pull request #1
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')#         # Replace with your GitHub personal access token

print("GITHUB_PR_NUMBER:", GITHUB_PR_NUMBER)

AZURE_OPENAI_ENDPOINT = 'https://attestopenai.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2025-01-01-preview'
AZURE_OPENAI_API_KEY =  os.getenv('AZURE_OPENAI_API_KEY') 

# Headers for GitHub API
github_headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# Headers for Azure OpenAI API
openai_headers = {
    'Content-Type': 'application/json',
    'api-key': AZURE_OPENAI_API_KEY
}

# Fetch PR metadata and commit messages from GitHub
def fetch_github_pr_metadata(owner: str, repo: str, pr_number: int) -> Dict:
    pr_url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}'
    commits_url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/commits'

    pr_response = requests.get(pr_url, headers=github_headers)
    commits_response = requests.get(commits_url, headers=github_headers)

    pr_data = pr_response.json()
    commits_data = commits_response.json()
    if isinstance(commits_data, dict) and "message" in commits_data:
        # API error, return empty commit messages
        commit_messages = []
    else:
        commit_messages = [commit['commit']['message'] for commit in commits_data]

    return {
        "id": pr_data["number"],
        "title": pr_data["title"],
        "description": pr_data.get("body", ""),
        "created_by": pr_data["user"]["login"],
        "created_at": pr_data["created_at"],
        "commit_messages": commit_messages
    }

# Generate summary using Azure OpenAI
def generate_summary(pr_metadata: Dict) -> str:
    prompt = f"Summarize the following pull request:\nTitle: {pr_metadata['title']}\nDescription: {pr_metadata['description']}\nCommits: {', '.join(pr_metadata['commit_messages'])}"
    payload = {
        "messages": [
            {"role": "system", "content": "You are an assistant that summarizes pull requests."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }
    response = requests.post(AZURE_OPENAI_ENDPOINT, headers=openai_headers, data=json.dumps(payload))
    result = response.json()
    return result['choices'][0]['message']['content']

# Assemble the agent output
def review_pull_request(owner: str, repo: str, pr_number: int) -> Dict:
    pr_metadata = fetch_github_pr_metadata(owner, repo, pr_number)
    return {
        "PR ID": pr_metadata["id"],
        "Title": pr_metadata["title"],
        "Summary": generate_summary(pr_metadata),
        "Created By": pr_metadata["created_by"],
        "Created At": pr_metadata["created_at"]
    }

# Run the agent
if __name__ == "__main__":
    #pr_review = review_pull_request(GITHUB_REPO_OWNER, GITHUB_REPO_NAME, GITHUB_PR_NUMBER)
    
        # Step 1: Get changed files
        files_url = f'https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/pulls/{GITHUB_PR_NUMBER}/files'
        print(files_url)
        files_response = requests.get(files_url, headers=github_headers)
        #files_data = files_response.json()
        
        try:
            files_data = files_response.json()
            if not isinstance(files_data, list):
                raise ValueError("Unexpected response format: not a list of files")
        except Exception as e:
            print("Error parsing GitHub response:", e)
            print("Response content:", files_response.text)
            exit(1)


        # Step 2: Build review prompt
        review_prompt = "Please review the following code changes for quality, security, anti-pattern, deprecarted methods and best practices.\n\n"
        for file in files_data:
            filename = file.get('filename', 'Unknown file')
            patch = file.get('patch', '[No patch available]')
            review_prompt += f"File: {filename}\nChanges:\n{patch}\n\n"


        # Step 3: Send to Azure OpenAI
        openai_payload = {
            "messages": [
                {"role": "system", "content": "You are a helpful code reviewer."},
                {"role": "user", "content": review_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }

        response = requests.post(AZURE_OPENAI_ENDPOINT, headers=openai_headers, json=openai_payload)
        review_result = response.json()

        # Step 4: Output review
        print("Code Review Result:")
        print(review_result['choices'][0]['message']['content'])

    # for key, value in pr_review.items():
    #     print(f"{key}: {value}")
