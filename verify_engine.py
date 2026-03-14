from ict_engine import ICTEngine
engine = ICTEngine()
print("Methods in ICTEngine:", [m for m in dir(engine) if not m.startswith("__")])
assert hasattr(engine, "ith_itl")
assert hasattr(engine, "find_ifvgs")
print("Validation Success!")
