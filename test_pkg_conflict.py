def test_import():
    # Simulate the directory structure and imports
    import os
    import sys

    os.makedirs("test_pkg", exist_ok=True)
    with open("test_pkg/my_mod.py", "w") as f:
        f.write("class MyObj:\n    def __init__(self):\n        self.name = 'instance'\nobj = MyObj()\n")

    with open("test_pkg/__init__.py", "w") as f:
        f.write("from .my_mod import obj as my_mod\n")

    sys.path.insert(0, ".")

    from test_pkg import my_mod

    print(f"my_mod is type: {type(my_mod)}")


if __name__ == "__main__":
    test_import()
