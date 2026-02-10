"""CraigPy CLI entry point."""

from __future__ import annotations

from pathlib import Path

import click

from craigpy import __version__
from craigpy.config.settings import load_settings, save_settings


@click.group()
@click.version_option(version=__version__, prog_name="craigpy")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """CraigPy — Local codebase indexer with semantic search."""
    ctx.ensure_object(dict)
    settings = load_settings()
    settings.ensure_dirs()
    ctx.obj["settings"] = settings


@cli.command()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Show current configuration."""
    settings = ctx.obj["settings"]
    click.echo(f"Config file:  {settings.config_dir / 'config.json'}")
    click.echo(f"Data dir:     {settings.data_dir}")
    click.echo(f"SQLite:       {settings.sqlite_path}")
    click.echo(f"ChromaDB:     {settings.chroma_path}")
    click.echo()
    click.echo("Defaults:")
    for key, value in settings.defaults.items():
        click.echo(f"  {key}: {value}")
    if settings.repos:
        click.echo()
        click.echo("Per-repo overrides:")
        for repo_path, overrides in settings.repos.items():
            click.echo(f"  {repo_path}:")
            for key, value in overrides.items():
                click.echo(f"    {key}: {value}")


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize craigpy config and data directories."""
    settings = ctx.obj["settings"]
    settings.ensure_dirs()
    if not (settings.config_dir / "config.json").exists():
        save_settings(settings)
        click.echo(f"Created config at {settings.config_dir / 'config.json'}")
    else:
        click.echo(f"Config already exists at {settings.config_dir / 'config.json'}")

    from craigpy.db.client import get_connection
    get_connection(settings.sqlite_path)
    click.echo(f"Database ready at {settings.sqlite_path}")


@cli.command()
@click.pass_context
def repos(ctx: click.Context) -> None:
    """List all indexed repositories."""
    settings = ctx.obj["settings"]
    from craigpy.db.client import get_connection
    from craigpy.db import queries

    conn = get_connection(settings.sqlite_path)
    repo_list = queries.list_repos(conn)

    if not repo_list:
        click.echo("No repositories indexed yet. Run 'craigpy ingest <path>' to get started.")
        return

    for repo in repo_list:
        file_count = queries.get_file_count(conn, repo["id"])
        ingested = repo["ingested_at"] or "never"
        click.echo(f"  {repo['name']:<30} {file_count:>6} files  (last indexed: {ingested})")
        click.echo(f"    path: {repo['path']}")


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option("--name", "-n", default=None, help="Repository name (defaults to directory name)")
@click.option("--force", "-f", is_flag=True, help="Re-index all files regardless of changes")
@click.pass_context
def ingest(ctx: click.Context, path: str, name: str | None, force: bool) -> None:
    """Ingest a repository for semantic search."""
    settings = ctx.obj["settings"]
    from craigpy.db.client import get_connection
    from craigpy.indexer.pipeline import ingest_repo

    conn = get_connection(settings.sqlite_path)
    repo_path = Path(path)

    def on_progress(msg: str) -> None:
        click.echo(f"  {msg}")

    click.echo(f"Indexing {repo_path}...")
    try:
        result = ingest_repo(
            conn=conn,
            settings=settings,
            repo_path=repo_path,
            name=name,
            force=force,
            on_progress=on_progress,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    click.echo()
    click.echo(f"Done! +{result['added']} added, ~{result['modified']} modified, -{result['deleted']} deleted")
    click.echo(f"  {result['chunks']} chunks indexed, {result['skipped']} files skipped")


@cli.command("ingest-file")
@click.argument("files", nargs=-1, type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--repo", "-r", required=True, help="Repository name")
@click.option("--threshold", "-t", default=None, type=int, help="Override chunk threshold")
@click.pass_context
def ingest_file(ctx: click.Context, files: tuple[str, ...], repo: str, threshold: int | None) -> None:
    """Force-ingest specific file(s) that were skipped due to size."""
    if not files:
        click.echo("No files specified.", err=True)
        raise SystemExit(1)

    settings = ctx.obj["settings"]
    from craigpy.db.client import get_connection
    from craigpy.indexer.pipeline import ingest_files

    conn = get_connection(settings.sqlite_path)
    file_paths = [Path(f) for f in files]

    try:
        result = ingest_files(
            conn=conn,
            settings=settings,
            repo_name=repo,
            file_paths=file_paths,
            threshold=threshold,
        )
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    click.echo(f"Done! {result['files']} files processed, {result['chunks']} chunks indexed")


@cli.command()
@click.option("--repo", "-r", default=None, help="Repository name (shows all if omitted)")
@click.pass_context
def status(ctx: click.Context, repo: str | None) -> None:
    """Show what changed since last index."""
    settings = ctx.obj["settings"]
    from craigpy.db.client import get_connection
    from craigpy.db import queries
    from craigpy.indexer.differ import compute_changeset
    from craigpy.indexer.file_filter import FileWalker
    from craigpy.indexer.merkle import hash_file

    conn = get_connection(settings.sqlite_path)

    if repo:
        repo_list = [queries.get_repo_by_name(conn, repo)]
        if repo_list[0] is None:
            click.echo(f"Repository '{repo}' not found.", err=True)
            raise SystemExit(1)
    else:
        repo_list = queries.list_repos(conn)

    if not repo_list:
        click.echo("No repositories indexed.")
        return

    for repo_row in repo_list:
        repo_path = Path(repo_row["path"])
        repo_config = settings.get_repo_config(str(repo_path))

        click.echo(f"{repo_row['name']} ({repo_path}):")

        if not repo_path.exists():
            click.echo("  Repository path no longer exists!")
            continue

        walker = FileWalker(repo_path, repo_config)
        files = walker.walk()

        file_hashes: dict[str, str] = {}
        for f in files:
            rel = str(f.relative_to(repo_path))
            file_hashes[rel] = hash_file(f)

        changeset = compute_changeset(conn, repo_row["id"], file_hashes)

        if not changeset.has_changes:
            click.echo("  Up to date")
        else:
            if changeset.added:
                click.echo(f"  +{len(changeset.added)} added")
                for f in changeset.added[:10]:
                    click.echo(f"    + {f}")
                if len(changeset.added) > 10:
                    click.echo(f"    ... and {len(changeset.added) - 10} more")
            if changeset.modified:
                click.echo(f"  ~{len(changeset.modified)} modified")
                for f in changeset.modified[:10]:
                    click.echo(f"    ~ {f}")
                if len(changeset.modified) > 10:
                    click.echo(f"    ... and {len(changeset.modified) - 10} more")
            if changeset.deleted:
                click.echo(f"  -{len(changeset.deleted)} deleted")
                for f in changeset.deleted[:10]:
                    click.echo(f"    - {f}")
                if len(changeset.deleted) > 10:
                    click.echo(f"    ... and {len(changeset.deleted) - 10} more")
        click.echo()


@cli.command()
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def purge(ctx: click.Context, name: str, yes: bool) -> None:
    """Purge a repository — removes all indexed data (ChromaDB + SQLite)."""
    settings = ctx.obj["settings"]
    from craigpy.db.client import get_connection
    from craigpy.db import queries

    conn = get_connection(settings.sqlite_path)
    repo = queries.get_repo_by_name(conn, name)

    if repo is None:
        click.echo(f"Repository '{name}' not found.", err=True)
        raise SystemExit(1)

    file_count = queries.get_file_count(conn, repo["id"])

    if not yes:
        click.echo(f"This will delete all indexed data for '{name}' ({file_count} files).")
        click.echo(f"  ChromaDB collection: {repo['collection_name']}")
        click.echo(f"  SQLite records: files, merkle nodes, repo entry")
        if not click.confirm("Proceed?"):
            click.echo("Aborted.")
            return

    # Delete ChromaDB collection
    import chromadb
    chroma_client = chromadb.PersistentClient(path=str(settings.chroma_path))
    try:
        chroma_client.delete_collection(name=repo["collection_name"])
        click.echo(f"Deleted ChromaDB collection '{repo['collection_name']}'")
    except ValueError:
        click.echo(f"ChromaDB collection '{repo['collection_name']}' not found (already clean)")

    # Delete from SQLite (cascades to files + merkle_nodes)
    queries.delete_repo(conn, repo["id"])
    click.echo(f"Deleted SQLite records for '{name}'")

    click.echo(f"Purged '{name}'. Run 'craigpy ingest {repo['path']}' to re-index.")
