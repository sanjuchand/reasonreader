from progress_store import save_progress


def test_save_progress_noops_without_user():
    save_progress(None, "copy", {"u0000": {"unlocked": True}})
    save_progress("user", None, {"u0000": {"unlocked": True}})
    save_progress("user", "copy", None)
    save_progress("user", "copy", {})
