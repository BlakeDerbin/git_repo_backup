import os.path
import requests
import json
import git
import logging
import sys
from datetime import datetime


class GithubBackup:
    def __init__(self, auth_token, api_url, github_name, is_org):
        self.auth_token = auth_token
        self.api_url = api_url
        self.github_name = github_name
        self.is_org = is_org
        self.clone_base_url = f'https://oauth2:{self.auth_token}@github.com/'
        self.api_org_url = f'{self.api_url}/orgs/{self.github_name}/repos'
        self.api_user_url = f'{self.api_url}/search/repositories?q=user:{self.github_name}'

    def fetch_github_repos(self):
        try:
            github_repos = [[], []]

            if self.is_org:
                request = requests.get(self.api_org_url, headers={'Authorization': f'token {self.auth_token}'})
                data = json.loads(request.text)

                for i in range(len(data)):
                    for k in data[i]:
                        if k == 'clone_url':
                            github_repos[0].append(data[i][k])
                        if k == 'name':
                            github_repos[1].append(data[i][k])
            else:
                request = requests.get(self.api_user_url, headers={'Authorization': f'token {self.auth_token}'})
                data = json.loads(request.text)

                for i in range(len(data['items'])):
                    for k in data['items'][i]:
                        if k == 'clone_url':
                            github_repos[0].append(data['items'][i][k])
                        if k == 'name':
                            github_repos[1].append(data['items'][i][k])

            return github_repos
        except OSError as e:
            logging.info(f"Error occured when fetching {self.github_name} repositories, error: {e}")
            sys.exit(1)

    def backup_github_repos(self, backup_path, github_repos, github_name):
        try:
            date_now = datetime.now().strftime("%d/%m/%Y - %I:%M %p")
            logging.info(f"[{date_now}] Starting backup for {github_name} repositories")

            for v in range(len(github_repos[0])):
                repo_name = github_repos[1][v]
                repo_url = github_repos[0][v]
                current_repo_dir = f'{backup_path}/{repo_name}'
                path_exists = os.path.exists(os.path.abspath(current_repo_dir))

                if path_exists:
                    os.chdir(current_repo_dir)
                    git.Git().remote('update')
                    git_status = git.Git().status("-uno")

                    if "up to date" in git_status:
                        logging.info(f"Repository up to date: {repo_name}")
                        os.chdir(backup_path)
                    elif "No commits yet" in git_status:
                        logging.info(f"No commits in repository: {repo_name}")
                        os.chdir(backup_path)
                    else:
                        git.Git().pull("-r", "--autostash")
                        logging.info(f"Pulled repository changes: {repo_name}")
                        os.chdir(backup_path)

                # handles repository cloning
                if not path_exists:
                    os.chdir(backup_path)
                    git.Git().clone(self.clone_base_url + repo_url.split("https://github.com/")[1],
                                    os.path.join(backup_path, repo_name))
                    logging.info(f"Cloned repository: {repo_name}")

            logging.info(f"All repositories for: {github_name} have been backed up")

        except OSError as e:
            logging.info(f"Error occured backing up repositories for {github_name}, error: {e}")
            sys.exit(1)
