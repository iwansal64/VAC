import sys, os

argv = list(sys.argv)

if argv[2] == "True":
    input(f"Arch wants to do this command: {argv[1]}? ")
os.system(f"zsh -is eval '{argv[1]}'")
