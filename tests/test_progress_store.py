from progress_store import save_progress


def test_save_progress_noops_without_user():
    save_progress(None, {"chap01": {"unlocked": True}})
    save_progress("user", None)
    save_progress("user", {})
