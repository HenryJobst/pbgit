from pathlib import Path
import git
import typer
from git import GitError

CWD = "."

app = typer.Typer()


def get_repo(working_dir: Path) -> git.Repo:
    if not working_dir.exists():
        typer.echo(f"Working directory {working_dir} does not exist. Abort rollout.")
        raise typer.Exit(1)

    try:
        repo = git.Repo(working_dir)
        return repo
    except GitError:
        typer.echo(f"No repository at {working_dir}. Abort rollout.")
        raise typer.Exit(1)


def is_bare_repo(repo: git.Repo) -> None:
    if repo.bare:
        typer.echo("Repository is a bare repo. Abort rollout.")
        raise typer.Exit(0)


def has_dirty_changes(repo: git.Repo) -> None:
    if repo.is_dirty() or len(repo.untracked_files) > 0:
        typer.echo("Uncommitted changes exist. Abort rollout.")
        raise typer.Exit(1)


def get_remote_repo(repo: git.Repo, remote_repo_name: str) -> git.Remote:
    if remote_repo_name not in repo.remotes:
        typer.echo(f"Remote repo {remote_repo_name} does not exist. Abort rollout.")
        raise typer.Exit(1)
    return repo.remotes[remote_repo_name]


def update_branch(repo: git.Repo, branch: str, verbose: bool = False) -> None:
    try:
        if verbose:
            typer.echo(f"Update {branch} branch...")
        validate_branch(repo, branch)
        repo.git.checkout(branch)
        repo.git.pull(rebase=True)
    except GitError:
        typer.echo(f"Update of {branch} branch failed. Abort rollout.")
        raise typer.Exit(1)


def validate_branch(repo: git.Repo, branch: str) -> None:
    if branch not in repo.heads:
        typer.echo(f"Branch {branch} does not exist. Abort rollout.")
        raise typer.Exit(1)


@app.command()
def rollout(
        working_dir: Path = CWD,
        base_branch: str = "main",
        pp_branch: str = "pre-production",
        prod_branch: str = "production",
        remote_repo_name: str = "origin",
        verbose: bool = False,
        skip_production: bool = False
):
    if working_dir == CWD:
        working_dir = Path.cwd()

    repo = get_repo(working_dir)
    is_bare_repo(repo)
    has_dirty_changes(repo)

    remote_repo = get_remote_repo(repo, remote_repo_name)
    remote_repo.fetch()

    update_branch(repo, base_branch, verbose)
    repo.git.push()

    update_branch(repo, pp_branch, verbose)
    repo.git.merge(base_branch)
    repo.git.push()

    if skip_production:
        raise typer.Exit(0)
    else:
        repo.git.checkout(base_branch)

    update_branch(repo, prod_branch, verbose)
    repo.git.merge(pp_branch)
    repo.git.push()

    repo.git.checkout(base_branch)


if __name__ == '__main__':
    app()
