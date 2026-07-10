import sys
from pathlib import Path

# the plugin lives in a Nikola plugin directory, not a package
sys.path.insert(0, str(Path(__file__).parent.parent / "plugins" / "causal_diagram"))
