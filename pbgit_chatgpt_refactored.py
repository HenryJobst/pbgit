from os import getcwd
import git
import typer
from git import GitError

CWD = "."

app = typer.Typer()


def get_repo(working_dir: str) -> git.Repo:
    try:
        repo = git.Repo(working_dir)
        return repo
    except GitError:
        typer.echo(f"No repository at {working_dir}. Abort rollout.")
        raise typer.Exit(1)


def is_bare_repo(repo: git.Repo) -> bool:
    if repo.bare:
        typer.echo("Repository is a bare repo. Abort rollout.")
        raise typer.Exit(0)
    return False


def has_dirty_changes(repo: git.Repo) -> bool:
    if repo.is_dirty() or len(repo.untracked_files) > 0:
        typer.echo("Uncommitted changes exist. Abort rollout.")
        raise typer.Exit(1)
    return False


def get_remote_repo(repo: git.Repo, remote_repo_name: str) -> git.Remote:
    try:
        remote_repo = repo.remotes[remote_repo_name]
        if not remote_repo:
            typer.echo(f"Remote repo {remote_repo_name} does not exist. Abort rollout.")
            raise typer.Exit(1)
        return remote_repo
    except IndexError:
        typer.echo(f"Remote repo {remote_repo_name} does not exist. Abort rollout.")
        raise typer.Exit(1)


def update_branch(repo: git.Repo, branch: str, verbose: bool = False):
    try:
        if verbose:
            typer.echo(f"Update {branch} branch...")
        repo.git.checkout(branch)
        repo.git.pull()
    except GitError:
        typer.echo(f"Update of {branch} branch failed. Abort rollout.")
        raise typer.Exit(1)


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
