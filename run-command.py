import sys, os

argv = list(sys.argv)

os.system(f"zsh -is eval '{argv[1]}'")
