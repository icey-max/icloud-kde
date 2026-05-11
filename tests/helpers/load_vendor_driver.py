"""Load the vendored icloud-linux driver with local dependency shims."""

from __future__ import annotations

import importlib.util
import sys
from io import BytesIO
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any


def load_vendor_driver() -> ModuleType:
    """Return the vendored `driver.py` module without requiring FUSE/pyicloud."""

    module_name = "icloud_kde_vendor_icloud_linux_driver"
    if module_name in sys.modules:
        return sys.modules[module_name]

    _install_fuse_shim()
    _install_pyicloud_shim()

    root = Path(__file__).resolve().parents[2]
    driver_path = root / "vendor" / "icloud-linux" / "driver.py"
    spec = importlib.util.spec_from_file_location(module_name, driver_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load vendored driver from {driver_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _install_fuse_shim() -> None:
    if "fuse" in sys.modules:
        return

    fuse = ModuleType("fuse")

    class Stat:
        pass

    class Fuse:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

        def parse(self, *args: Any, **kwargs: Any) -> None:
            return None

        def main(self, *args: Any, **kwargs: Any) -> None:
            return None

    fuse.Stat = Stat
    fuse.Fuse = Fuse
    fuse.__version__ = "0.2"
    fuse.fuse_python_api = (0, 2)
    sys.modules["fuse"] = fuse


def _install_pyicloud_shim() -> None:
    if "pyicloud" in sys.modules:
        return

    pyicloud = ModuleType("pyicloud")
    exceptions = ModuleType("pyicloud.exceptions")
    services = ModuleType("pyicloud.services")
    drive = ModuleType("pyicloud.services.drive")

    class PyiCloudService:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

    class PyiCloud2FARequiredException(Exception):
        pass

    class PyiCloud2SARequiredException(Exception):
        pass

    class PyiCloudAPIResponseException(Exception):
        def __init__(self, reason: str, code: int | None = None) -> None:
            super().__init__(reason)
            self.reason = reason
            self.code = code

    class PyiCloudAuthRequiredException(Exception):
        pass

    class PyiCloudFailedLoginException(Exception):
        pass

    class DriveNode:
        def __init__(self, drive_service: Any, data: dict[str, Any]) -> None:
            self.drive_service = drive_service
            self.data = data
            self.children: list[DriveNode] = []
            self.uploads: list[bytes] = []

        @property
        def name(self) -> str:
            return str(self.data.get("name", ""))

        def open(self, stream: bool = True) -> SimpleNamespace:
            del stream
            return SimpleNamespace(raw=BytesIO(self.data.get("_content", b"")))

        def rename(self, new_name: str) -> None:
            self.data["name"] = new_name

        def delete(self) -> None:
            self.data["_deleted"] = True

        def upload(self, file_obj: Any) -> "DriveNode":
            content = file_obj.read()
            self.uploads.append(content)
            child = DriveNode(
                self.drive_service,
                {
                    "drivewsid": f"uploaded-{len(self.uploads)}",
                    "docwsid": f"uploaded-doc-{len(self.uploads)}",
                    "etag": f"uploaded-etag-{len(self.uploads)}",
                    "zone": "fake-zone",
                    "type": "FILE",
                    "name": getattr(file_obj, "name", "uploaded"),
                    "size": len(content),
                    "_content": content,
                },
            )
            self.children.append(child)
            return child

        def mkdir(self, name: str) -> "DriveNode":
            child = DriveNode(
                self.drive_service,
                {
                    "drivewsid": f"folder-{len(self.children) + 1}",
                    "type": "FOLDER",
                    "name": name,
                    "size": 0,
                },
            )
            self.children.append(child)
            return child

        def get_children(self, force: bool = False) -> list["DriveNode"]:
            del force
            return list(self.children)

    pyicloud.PyiCloudService = PyiCloudService
    exceptions.PyiCloud2FARequiredException = PyiCloud2FARequiredException
    exceptions.PyiCloud2SARequiredException = PyiCloud2SARequiredException
    exceptions.PyiCloudAPIResponseException = PyiCloudAPIResponseException
    exceptions.PyiCloudAuthRequiredException = PyiCloudAuthRequiredException
    exceptions.PyiCloudFailedLoginException = PyiCloudFailedLoginException
    drive.DriveNode = DriveNode

    sys.modules["pyicloud"] = pyicloud
    sys.modules["pyicloud.exceptions"] = exceptions
    sys.modules["pyicloud.services"] = services
    sys.modules["pyicloud.services.drive"] = drive

