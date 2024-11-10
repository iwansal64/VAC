import os, sys, readline, datetime
print("Welcome to Virtual Arch Client!")


config_file_path = f"/home/{os.getlogin()}/.config/vac/config.json"
message_folder_path = f"/home/{os.getlogin()}/.var/vac/messages"


argv = list(sys.argv)
if len(sys.argv) <= 0:
    print("Please provide config file path!")
    exit(0)

while True:
    print("Message VAC:")
    message = input()
    
    with open(message_folder_path + f"/message-{datetime.datetime.now().strftime(r"%d-%m-%Y %H-%M-%S")}.vac", "w") as message_file:
        message_file.write(message)
        
    if message == "/bye":
        break
    
    