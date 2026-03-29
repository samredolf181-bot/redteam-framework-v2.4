from framework.db.database import db
from framework.core.workspace_manager import WorkspaceManager


def test_workspace_crud(tmp_path):
    db.init(str(tmp_path / "t.db"))
    wm = WorkspaceManager()
    ws = wm.create({"name": "Case A"})
    assert ws["name"] == "Case A"
    ws2 = wm.update(ws["id"], {"status": "active", "description": "x"})
    assert ws2 and ws2["description"] == "x"
