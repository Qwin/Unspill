"""A simple terminal recovery picker with explicit actions and safe cancellation."""

from pathlib import Path
import sys

from .navigation import entry_text, file_diff, file_history, numbered, preview, preview_text
from .storage import UnspillError


def recover_interactively(repo):
    if not sys.stdin.isatty():
        raise UnspillError("Interactive recovery needs a terminal. Use timeline, restore ID --dry-run, or recover ID --to DIRECTORY.")
    repo.require_idle()
    try:
        print("What would you like to recover?\n1. Before my last operation\n2. An earlier version of a file\n3. A branch or stash operation\n4. Browse the full timeline\nEnter/q. Cancel")
        choice = input("> ").strip()
        selected_path = None
        records = numbered(repo)
        if choice == "1":
            records = [s for s in records if s["kind"] in {"before-command", "before-restore"}][-1:]
        elif choice == "2":
            selected_path = input("Repository-relative file path: ").strip()
            records = file_history(repo, selected_path)
        elif choice == "3":
            records = [s for s in records if "git branch" in s["label"] or "git stash" in s["label"]]
        elif choice != "4":
            print("Cancelled. Nothing changed.")
            return
        if not records:
            raise UnspillError("No matching checkpoints. Try browsing the full timeline.")
        for snapshot in reversed(records):
            print(entry_text(snapshot) + "\n")
        selector = input("Choose @number (Enter to cancel): ").strip()
        if not selector:
            print("Cancelled. Nothing changed.")
            return
        selected = repo.load(selector)
        if selected["id"] not in {s["id"] for s in records}:
            raise UnspillError("Choose one of the checkpoints shown above.")
        print(preview_text(preview(repo, selected)))
        while True:
            print("\nd. Inspect a file's text differences\nr. Restore the WHOLE checkpoint (saves current state first)\ne. Export to a new folder\nEnter/q. Cancel")
            action = input("> ").strip().lower()
            if action == "d":
                path = selected_path or input("Repository-relative file path: ").strip()
                print(file_diff(repo, selected, path))
            elif action == "r":
                checkpoint = repo.restore(selected["id"])
                print(f"Restored. Previous state retained as {checkpoint['id']}")
                return
            elif action == "e":
                destination = input("New destination folder (Enter to cancel): ").strip()
                if not destination:
                    print("Cancelled. Nothing changed.")
                    return
                repo.recover(selected["id"], Path(destination), selected_path)
                print(f"Recovered to {Path(destination).absolute()}; current repository unchanged.")
                return
            else:
                print("Cancelled. Nothing changed.")
                return
    except EOFError:
        print("Cancelled. Nothing changed.")
