# Git Repo Backup
The purpose of this script is to provide a solution for backing up repositories from both Gitlab and Github.

Gitlab's API by default will ask for a 2FA code when getting an archive of a repository, it is also limited to 5 requests per minute for Gitlab.com users. This script uses the module gitpython to clone in new repositories and pull in changes for existing repositories. 

This script also support exporting repositories from a Gitlab export, currently the format that works with this is a single tarfile of any gitlab exports you wish to extract the gitlab repositories from. If you want to use this you will need to toggle this on in the config.yaml.\

Github repositories can also be backed up as well from both multiple users, and organizations.

By default the script will generate 2 outputs when backing up a repository:
* backup directory ( stores repositories and pulls in changes to them from remote )
* tarfile of the backup directory ( only generated once per day )

Both of these outputs can have their own directories by either specifying them in the config.yaml or when running the script using the user args.

## Requirements
To use this backup script you will need the following pip modules installed:
* Pip modules: requests, gitpython

For each backup method you can set the values in the config.yaml
#### If you have gitlab backups enabled:

* A Gitlab token with both api_read & read_repository access
* Your group_id/s for the gitlab group

#### If you have Github backups enabled
* A Github personal access token with full repo access
* A user/s and/or a Github organization/s

If you have Singularity installed you can also build the python_with_modules.def file for a container with everything needed to use the script.
