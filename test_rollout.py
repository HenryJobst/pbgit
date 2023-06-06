import pytest
from git import Repo
from pathlib import Path
from typer.testing import CliRunner

from pbgit_chatgpt_further_refactored import app

BASE_BRANCH = "main"
PP_BRANCH = "pre-production"
PROD_BRANCH = "production"
REMOTE_REPO_NAME = "origin"

TEST_REPO_DIR = Path(__file__).resolve().parent / "test_repo"
TEST_REMOTE_REPO_DIR = Path(__file__).resolve().parent / "test_remote_repo"


@pytest.fixture(scope="session", autouse=True)
def setup_test_repo():
    if not TEST_REPO_DIR.exists():
        Repo.init(TEST_REPO_DIR)
        repo = Repo(TEST_REPO_DIR)
        open(TEST_REPO_DIR / "test_file.txt", "w").close()
        repo.index.add(["test_file.txt"])
        repo.index.commit("Initial commit")
        repo.create_remote(REMOTE_REPO_NAME, str(TEST_REMOTE_REPO_DIR))
        repo.remote(REMOTE_REPO_NAME).push(BASE_BRANCH)
        repo.create_head(PP_BRANCH)
        repo.create_head(PROD_BRANCH)


@pytest.fixture(scope="session", autouse=True)
def setup_test_remote_repo():
    if not TEST_REMOTE_REPO_DIR.exists():
        Repo.init(TEST_REMOTE_REPO_DIR)
        remote_repo = Repo(TEST_REMOTE_REPO_DIR)
        open(TEST_REMOTE_REPO_DIR / "test_file.txt", "w").close()
        remote_repo.index.add(["test_file.txt"])
        remote_repo.index.commit("Initial commit")
        remote_repo.create_head(PP_BRANCH)
        remote_repo.create_head(PROD_BRANCH)


def test_rollout_success():
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "--working-dir",
                str(TEST_REPO_DIR),
                "--base-branch",
                BASE_BRANCH,
                "--pp-branch",
                PP_BRANCH,
                "--prod-branch",
                PROD_BRANCH,
                "--remote-repo-name",
                REMOTE_REPO_NAME,
                "--skip-production",
            ],
        )

        assert 0 == result.exit_code
        assert "Rollout successful" in result.stdout


def test_rollout_dirty_changes():
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create a dirty change in the test repository
        dirty_file_path = TEST_REPO_DIR / "dirty_file.txt"
        with open(dirty_file_path, "w") as f:
            f.write("Dirty change")

        result = runner.invoke(
            app,
            [
                "--working-dir",
                str(TEST_REPO_DIR),
                "--base-branch",
                BASE_BRANCH,
                "--pp-branch",
                PP_BRANCH,
                "--prod-branch",
                PROD_BRANCH,
                "--remote-repo-name",
                REMOTE_REPO_NAME,
                "--skip-production",
            ],
        )

        assert result.exit_code != 0
        assert "Check for uncommitted changes failed" in result.stdout


def test_rollout_missing_remote_repo():
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "--working-dir",
                str(TEST_REPO_DIR),
                "--base-branch",
                BASE_BRANCH,
                "--pp-branch",
                PP_BRANCH,
                "--prod-branch",
                PROD_BRANCH,
                "--remote-repo-name",
                "nonexistent_remote",
                "--skip-production",
            ],
        )

        assert result.exit_code != 0
        assert "Remote repo nonexistent_remote does not exist" in result.stdout


def test_rollout_missing_branch():
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "--working-dir",
                str(TEST_REPO_DIR),
                "--base-branch",
                "nonexistent_branch",
                "--pp-branch",
                PP_BRANCH,
                "--prod-branch",
                PROD_BRANCH,
                "--remote-repo-name",
                REMOTE_REPO_NAME,
                "--skip-production",
            ],
        )

        assert result.exit_code != 0
        assert "Update of nonexistent_branch branch failed" in result.stdout

