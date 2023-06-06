from os import getcwd

import git
import typer
from git import GitError

CWD = "."

app = typer.Typer()


def get_repo(working_dir: str) -> git.Repo | None:
    try:
        repo = git.Repo(working_dir)
        return repo
    except GitError:
        typer.echo(f"No repository at {working_dir}.")
        return None


def not_bare(repo: git.Repo) -> bool:
    return not repo.bare


def not_dirty(repo: git.Repo) -> bool:
    return not repo.is_dirty() and len(repo.untracked_files) == 0


def get_remote_repo(repo: git.Repo, remote_repo_name: str) -> git.Remote | None:
    try:
        remote_repo = repo.remotes[remote_repo_name]
        if not remote_repo:
            typer.echo(f"Remote repo {remote_repo_name} does not exist.")
            return None
        return remote_repo
    except IndexError:
        typer.echo(f"Remote repo {remote_repo_name} does not exist.")
        return None


def validate_branch(repo: git.Repo, branch: str) -> None:
    if branch not in repo.heads:
        typer.echo(f"Branch {branch} does not exist. Abort rollout.")
        raise typer.Exit(1)


def update_branch(repo: git.Repo, branch: str, remote_repo_name: str, verbose: bool = False) -> bool:
    try:
        if verbose:
            typer.echo(f"Update {branch} branch...")
        validate_branch(repo, branch)
        repo.git.checkout(branch)
        if not repo.heads[branch].tracking_branch():
            repo.heads[branch].set_tracking_branch(repo.remote(remote_repo_name).refs[branch])
        repo.git.pull(rebase=True)
        return True
    except GitError:
        typer.echo(f"Update of {branch} branch failed.")
        return False


def merge_branch(repo: git.Repo, source_branch: str, target_branch: str, verbose: bool = False) -> bool:
    try:
        if verbose:
            typer.echo(f"Merge {source_branch} branch to {target_branch} branch...")
        repo.git.merge(source_branch)
        repo.git.push()
        return True
    except GitError:
        typer.echo(f"Merge of {source_branch} branch to {target_branch} branch failed.")
        return False


def merge_base_to_pp_branch(repo: git.Repo,
                            base_branch: str,
                            pp_branch: str,
                            remote_repo_name: str,
                            verbose: bool = False) -> bool:
    return update_branch(repo, pp_branch, remote_repo_name, verbose) and merge_branch(repo,
                                                                                      base_branch,
                                                                                      pp_branch,
                                                                                      verbose)


def merge_pp_to_prod_branch(repo: git.Repo,
                            pp_branch: str,
                            prod_branch: str,
                            remote_repo_name: str,
                            verbose: bool = False) -> bool:
    return update_branch(repo, prod_branch, remote_repo_name, verbose) and merge_branch(repo,
                                                                                        pp_branch,
                                                                                        prod_branch,
                                                                                        verbose)


def checkout_branch(repo: git.Repo, branch: str, verbose: bool = False) -> bool:
    try:
        if verbose:
            typer.echo(f"Checkout branch {branch}...")
        repo.git.checkout(branch)
        return True
    except GitError:
        typer.echo(f"Checkout of {branch} branch failed.")
        return False


def rollout_step(step_name: str, verbose: bool, func, *args, **kwargs) -> bool:
    try:
        result = func(*args, **kwargs)
        if result:
            if verbose:
                typer.echo(f"{step_name} completed successfully.")
        else:
            typer.echo(f"{step_name} failed. Abort rollout.")
        return result
    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"{step_name} failed with exception: {str(e)}")
        return False


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

    repo = get_repo(working_dir)
    if repo is None:
        raise typer.Exit(1)

    steps = [
        ("Check for uncommitted changes", not_dirty, repo),
        ("Check if repository is bare", not_bare, repo),
        ("Get remote repository", get_remote_repo, repo, remote_repo_name),
        ("Fetch remote repository", lambda repos, remote_name: repos.remotes[remote_name].fetch(), repo,
         remote_repo_name),
        ("Update base branch", update_branch, repo, base_branch, remote_repo_name, verbose),
        ("Merge base branch to pp branch", merge_base_to_pp_branch, repo, base_branch, pp_branch, remote_repo_name,
         verbose)
        ]

    if not skip_production:
        steps.extend([
            ("Merge pp branch to production branch", merge_pp_to_prod_branch, repo, pp_branch, prod_branch,
             remote_repo_name, verbose)
            ])

    steps.extend([
        ("Checkout base branch", checkout_branch, repo, base_branch, verbose)
        ])

    for step_name, func, *args in steps:
        if not rollout_step(step_name, verbose, func, *args):
            rollout_step("Checkout base branch", verbose, checkout_branch, repo, base_branch, verbose)
            raise typer.Exit(1)


if __name__ == '__main__':
    app()
