import sys
from robodk.robolink import Robolink

def test_load_by_name():
    RDK = Robolink()
    robot_name = "ABB CRB 1300-7/1.4" # Or "UR10"
    print(f"Attempting to load {robot_name}...")
    
    # AddFile usually looks in local library.
    # For online, we might need a URL or RoboDK handles it if connected to internet?
    # Documentation says: "AddFile(filename, parent=0, visible=True): Load a file... from a local path or a web URL."
    
    # Let's try a known online URL or just the name if RoboDK is smart.
    # Usually "UR10.robot" works if it's in the default library path.
    
    item = RDK.AddFile(robot_name)
    if item.Valid():
        print(f"Success! Loaded {item.Name()}")
        item.Delete()
    else:
        print("Failed to load by name.")

if __name__ == "__main__":
    test_load_by_name()
