from robodk.robolink import Robolink
RDK = Robolink()
try:
    RDK.OpenLibrary()
    print("OpenLibrary called successfully.")
except AttributeError:
    print("OpenLibrary not found.")
