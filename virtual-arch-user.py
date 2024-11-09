import os, sys
print("Welcome to Virtual Arch Client!")


config_file_path = f"/home/{os.getlogin()}/.config/vac/config.json"
message_file_path = f"/home/{os.getlogin()}/.config/vac/virtual-arch-message.txt"


argv = list(sys.argv)
if len(sys.argv) <= 0:
    print("Please provide config file path!")
    exit(0)

while True:
    message = input("Message VAC > ")
    
    with open(message_file_path, "w") as message_file:
        message_file.write(message)
        
    if message == "/bye":
        break
    
    