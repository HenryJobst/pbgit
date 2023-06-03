from os import getcwd

import git
import typer
from git import GitError

CWD = "."

app = typer.Typer()


@app.command()
def rollout(
        working_dir: str = CWD,
        base_branch: str = "main",
        pp_branch: str = "pre-production",
        prod_branch: str = "production",
        remote_repo_name: str = "origin",
        verbose: bool = False,
        skip_production: bool = False
        ):

    if working_dir == CWD:
        working_dir = getcwd()

    try:
        repo = git.Repo(working_dir)
    except GitError:
        print("No repository at ", working_dir, ". Abort rollout.")
        exit(1)

    if repo.bare:
        print("Repository is a bare repo. Abort rollout.")
        exit(0)

    print("Active branch:", repo.active_branch.name) if verbose else None

    if repo.is_dirty() or len(repo.untracked_files) > 0:
        print("Uncommited changes exists. Abort rollout.")
        exit(1)

    try:
        remote_repo = repo.remotes[remote_repo_name]
        if not remote_repo:
            print("Remote repo", remote_repo_name, "not exists. Abort rollout.")
    except IndexError:
        print("Remote repo", remote_repo_name, "not exists. Abort rollout.")
        exit(1)

    remote_repo.fetch()

    try:
        print("Update base branch...") if verbose else None
        repo.git.checkout(base_branch)
        repo.git.pull()
        repo.git.push()
    except GitError:
        print("Update of base branch", base_branch, "failed. Abort rollout.")
        exit(1)

    try:
        print("Update pp branch...") if verbose else None
        repo.git.checkout(pp_branch)
        repo.git.pull()
    except GitError:
        print("Update of pp branch", pp_branch, "failed. Abort rollout.")
        exit(1)

    print("Merge base branch to pp branch...") if verbose else None
    repo.git.merge(base_branch)
    print("Push pp branch...") if verbose else None
    repo.git.push()

    if skip_production:
        repo.git.checkout(base_branch)
        exit(0)

    try:
        print("Update production branch...") if verbose else None
        repo.git.checkout(prod_branch)
        repo.git.pull()
    except GitError:
        print("Update of production branch", prod_branch, "failed. Abort rollout.")
        exit(1)

    print("Merge pp branch to production branch...") if verbose else None
    repo.git.merge(pp_branch)
    print("Push production branch...") if verbose else None
    repo.git.push()

    repo.git.checkout(base_branch)


if __name__ == '__main__':
    app()
