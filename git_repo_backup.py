import sys
import errno
import stat
import os
import shutil
import logging
from pathlib import Path
from scripts import config, zip_repos, github as github_s, gitlab as gitlab_s


if __name__ == '__main__':
    config = config.config_yaml()
    github = config['github']
    gitlab = config['gitlab']
    gitlab_export = config['gitlab_export']

    log_file_path = (config['logfile_directory'], f'{Path.cwd}/gitlab_backup.log')[config['logfile_directory'] is None]

    # gitlab clone group projects config variables
    gitlab_enable_backup = (gitlab['enable'], False)[gitlab['enable'] is None]
    gitlab_token = gitlab['auth_token']
    gitlab_group_ids = (gitlab['group_ids'], None)[gitlab['group_ids'] == '' or gitlab['group_ids'] is None]
    gitlab_api_url = gitlab['api_url']

    gitlab_remove_repo_dir = gitlab['backups']['remove_directory']
    gitlab_backup_path = gitlab['backups']['repo_path']
    gitlab_zip_path = (gitlab['backups']['zip_export_path'], Path.cwd())[gitlab['backups']['zip_export_path'] is None]
    gitlab_generate_zip = (gitlab['backups']['generate_zip_export'], False)[gitlab['backups']['generate_zip_export'] is None]
    gitlab_zip_storage_count = gitlab['backups']['zip_storage']

    # gitlab group project export config variables
    gitlab_group_export = (gitlab_export['enable'], False)[gitlab_export['enable'] is None]
    gitlab_export_dir = gitlab_export['export_directory']
    gitlab_export_tar = gitlab_export['export_tarfile_path']

    # github backup config variables
    github_enable_backup = (github['enable'], False)[github['enable'] is None]
    github_api_url = github['api_url']
    github_auth_token = github['auth_token']
    github_org_names = (github['org_name'], None)[github['org_name'] == '' or github['org_name'] is None]
    github_user_names = (github['user_name'], None)[github['user_name'] == '' or github['user_name'] is None]

    github_remove_repo_dir = github['backups']['remove_directory']
    github_backup_path = github['backups']['repo_path']
    github_zip_path = (github['backups']['zip_export_path'], Path.cwd())[gitlab['backups']['zip_export_path'] is None]
    github_generate_zip = (github['backups']['generate_zip_export'], False)[gitlab['backups']['generate_zip_export'] is None]
    github_zip_storage_count = github['backups']['zip_storage']

    try:
        # Makes logfile directory if it doesn't exist
        log_file_dir = log_file_path.rsplit("/", 1)[0]
        log_file_name = log_file_path.rsplit("/", 1)[1]

        if os.path.exists(log_file_dir):
            logging.basicConfig(filename=log_file_path, level=logging.INFO)
        else:
            os.makedirs(log_file_dir)
            logging.basicConfig(filename=log_file_path, level=logging.INFO)
    except OSError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Checks if config values are present for gitlab and github
    if gitlab_enable_backup and gitlab_group_ids is None:
        logging.error(f"Gitlab backups enabled with no group_ids, exiting...")
        print(f"Gitlab backups enabled with no group_ids, exiting...")
        if github_enable_backup and github_user_names is None and github_org_names is None:
            logging.error("Github backups are enabled with no org_name or user_name provided, exiting...")
            print("Github backups are enabled with no org_name or user_name provided, exiting...")
            sys.exit(1)
        else:
            sys.exit(1)

    def create_directory(dir_in):
        # Creates directory
        try:
            path_exists = os.path.exists(dir_in)

            if not path_exists:
                os.makedirs(dir_in)
                logging.info(f"Created directory: {dir_in}")

        except OSError as e:
            logging.error(f"Unable to create directory: {dir_in}, error: {e}")
            sys.exit(1)


    def remove_directory(backup_path_in):
        # Removes backup directory when the flag -r is used
        try:
            shutil.rmtree(backup_path_in, ignore_errors=False, onerror=handle_remove_readonly)
            logging.warning(f"Removed directory: {backup_path_in}")

        except OSError as e:
            logging.info(f"Unable to remove backup directory: {backup_path_in} error: {e}")


    def handle_remove_readonly(func, path, exc):
        # Handles removing directory if errors occur
        excvalue = exc[1]
        if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
            func(path)
        else:
            raise

    # Handles gitlab backups from group_id
    if gitlab_enable_backup and gitlab_group_ids is not None:
        gitlab_group_ids = gitlab_group_ids.split(',')
        for group in gitlab_group_ids:
            gitlab_backup = gitlab_s.GitlabBackup(gitlab_token, group.strip(), gitlab_api_url)
            group_projects, group_name = gitlab_backup.fetch_group_projects()

            zip_filename = f'gitlab_{group_name.lower()}'
            backup_dir_name = f'gitlab_{group_name.lower()}_backups'
            full_backup_path = os.path.join(github_backup_path, backup_dir_name)

            create_directory(full_backup_path)

            gitlab_backup.backup_group_repositories(full_backup_path, group_projects)

            # handles zipping gitlab projects
            if gitlab_generate_zip:
                create_directory(gitlab_zip_path)
                gitlab_zip = zip_repos.ZipRepositories(
                    zip_filename,
                    gitlab_zip_path,
                    gitlab_zip_storage_count,
                    full_backup_path,
                    gitlab_backup_path
                )
                gitlab_zip.backup_group_projects_to_tar()

            if gitlab_remove_repo_dir:
                remove_directory(full_backup_path)

            logging.info(f"Gitlab backups for: {group_name} SUCCESSFUL\n")
            print(f"Gitlab backups for: {group_name} SUCCESSFUL\n")

    # Handles group backups from gitlab group export of projects
    if gitlab_group_export:
        gitlab_export = gitlab_s.GitlabExport(gitlab_export_dir, gitlab_export_tar)
        gitlab_export.backup_group_export()

        logging.info(f"Gitlab group project export from tarfile: {gitlab_export_tar} SUCCESSFUL\n")
        print(f"Gitlab group project export from tarfile: {gitlab_export_tar} SUCCESSFUL\n")

    if github_org_names is not None and github_enable_backup:
        github_org_names = github_org_names.split(",")
        for n in github_org_names:
            org_name = n.replace(" ", "")
            github_backup = github_s.GithubBackup(github_auth_token, github_api_url, org_name, True)
            github_org_repos = github_backup.fetch_github_repos()

            github_backup_dir = f'github_{org_name.lower()}_backups'
            full_org_backup_path = f'{github_backup_path}/{github_backup_dir}'
            create_directory(full_org_backup_path)
            github_backup.backup_github_repos(full_org_backup_path, github_org_repos, org_name)

            if github_generate_zip:
                create_directory(github_zip_path)
                github_org_zip = zip_repos.ZipRepositories(
                    f'github_{org_name.lower()}',
                    github_zip_path,
                    github_zip_storage_count,
                    full_org_backup_path,
                    github_backup_path
                )
                github_org_zip.backup_group_projects_to_tar()

            if github_remove_repo_dir:
                remove_directory(full_org_backup_path)

            logging.info(f"Github backups for: {org_name} SUCCESSFUL\n")
            print(f"Github backups for: {org_name} SUCCESSFUL\n")

    if github_user_names is not None and github_enable_backup:
        github_user_names = github_user_names.split(",")
        for n in github_user_names:
            user_name = n.replace(" ", "")
            github_backup = github_s.GithubBackup(github_auth_token, github_api_url, user_name, False)
            github_user_repos = github_backup.fetch_github_repos()

            github_backup_dir = f'github_{user_name.lower()}_backups'
            full_user_backup_path = f'{github_backup_path}/{github_backup_dir}'
            create_directory(full_user_backup_path)
            github_backup.backup_github_repos(full_user_backup_path, github_user_repos, user_name)

            if github_generate_zip:
                create_directory(github_zip_path)
                github_user_zip = zip_repos.ZipRepositories(
                    f'github_{user_name.lower()}',
                    github_zip_path,
                    github_zip_storage_count,
                    full_user_backup_path,
                    github_backup_path
                )
                github_user_zip.backup_group_projects_to_tar()

            if github_remove_repo_dir:
                remove_directory(full_user_backup_path)

            logging.info(f"Github backups for: {user_name} SUCCESSFUL\n")
            print(f"Github backups for: {user_name} SUCCESSFUL\n")
