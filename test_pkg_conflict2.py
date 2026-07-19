def test_import():
    # Simulate the directory structure and imports
    import os
    import sys

    os.makedirs("test_pkg2", exist_ok=True)
    with open("test_pkg2/router.py", "w") as f:
        f.write(
            "class StateRouter:\n    def dispatch(self):\n        print('dispatch called!')\nrouter = StateRouter()\n"
        )

    with open("test_pkg2/__init__.py", "w") as f:
        f.write("from .router import router\n")

    sys.path.insert(0, ".")

    from test_pkg2 import router

    print(f"router is type: {type(router)}")
    if hasattr(router, "dispatch"):
        print("router HAS dispatch method!")
    else:
        print("router is a module, NO dispatch method!")


if __name__ == "__main__":
    test_import()
