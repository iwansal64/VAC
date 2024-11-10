import os, subprocess, sys, json, time, ollama, threading, datetime, io
from typing import Tuple, Mapping, Iterator

HOME = f"/home/{os.getlogin()}"
VERSION = "0.8"

#? Colors that we'll use later!
RED_COLOR = "\033[0;31m"
GREEN_COLOR = "\033[0;32m"
WHITE_COLOR = "\033[0;37m"
GREEN_BOLD_COLOR = "\033[1;32m"
BLUE_BOLD_COLOR = "\033[1;34m"
YELLOW_BOLD_COLOR = "\033[1;33m"

USER_TEXT_COLOR = GREEN_BOLD_COLOR
ARCH_TEXT_COLOR = BLUE_BOLD_COLOR
AFK_TEXT_COLOR = YELLOW_BOLD_COLOR

#? Used to synchronize the AI side to the USER side
running = True

#? Used to keep track of context
current_context = []

#? Used to make the AI talk to the user wherever the wait time is up
wait_time = -1

#? Used to keep tracking of how many times the user afk
afk_count = 0


#? Configration file path... You can change it if you want to make it permanently change :)
configuration_file_path = f"{HOME}/.config/vac/config.json"

#? Message file path
message_folder_path = ""

#? Save messages history
save_messages_history = False

def print_error(title: str, message: str) -> None:
    '''
    Print an error message
    '''
    print(f"{RED_COLOR}[{title}] {WHITE_COLOR}{message}")

def print_success(title: str, message: str="") -> None:
    '''
    Print a successful message
    '''
    print(f"{GREEN_COLOR}[{title}] {WHITE_COLOR}{message}")
    
def cmd(command: str) -> Tuple[bytes, int]:
    '''
    Function that used for getting the output and status code (if there's an error it'll output outside 0)
    '''
    res = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return (str(res.stdout.read())[2:-3].replace("\\n", "\n"), res.wait())

cmd_threads: list[threading.Thread] = []

def open_cmd(command: str) -> None:
    '''
    Open CMD to run commands by the AI
    '''
    global cmd_threads
    cmd(f"kitty sh ./open_cmd.sh '{command}' & disown")
    del cmd_threads[-1]

def open_user_side() -> None:
    '''
    Open the client side in new window
    '''
    global running

    cmd("kitty sh ./open_user_side.sh & disown")
    running = False


client_thread = threading.Thread(target=open_user_side)

def debug(message:str):
    '''
    Function that used to log a debug
    '''
    if "debug-file-path" in user_configurations and user_configurations.get("debug-file-path") != "":
        with open(user_configurations.get("debug-file-path"), "a+") as f:
            f.write(f"[{datetime.datetime.now().strftime(r"%d/%m/%Y %H:%M:%S")}]{message}\n")

def send_req_to_ai(command: str, model: str) -> Iterator[Mapping[str, str]]:
    '''
    Function that used to send prompt to the AI
    '''
    global current_context
    try:
        res = ollama.generate(
            model=model,
            prompt=command,
            context=current_context,
            stream=True
        )

        return res
    except Exception as e:
        print_error("SENDING MESSAGE ERROR", e)
        exit(0)

def generate_response(response_iterator: Iterator[Mapping[str, str]], update_context=True):
    '''
    Used to generating response
    '''
    global wait_time
    global current_context
    global afk_count
    
    next_value = ""

    for response_item in response_iterator:
        response = response_item.get("response")

        if "[" in response or next_value != "":
            debug(response)
            next_value += response
            
            end_of_system_command = "]" in next_value
            if end_of_system_command:
                debug(next_value)
                debug("END OF SYSTEM COMMAND")

            #? Maximum amount of auto chat is 2
            if afk_count + 1 < 2 and next_value.replace(" ", "").startswith("[wt:") and end_of_system_command:
                next_value = next_value.replace(" ", "") #? Removes spaces
                next_value = next_value.replace("wt", "") #? Removes 'wt'
                next_value = next_value.replace(":", "") #? Removes ':'
                next_value = next_value.replace("[", "") #? Removes open parentheses
                next_value = next_value.replace("]", "") #? Removes close parentheses

                if next_value == "N/A":
                    wait_time = -1
                else:
                    try:
                        wait_time = int(next_value) + 10
                        debug(f"wait_time ({next_value}) is a number")
                    except ValueError:
                        debug(f"wait_time ({next_value}) is not a number")


            if next_value.replace(" ", "").startswith("[cmd:") and end_of_system_command:
                next_value = next_value.replace("cmd", "") #? Removes 'wt'
                next_value = next_value.replace(":", "") #? Removes ':'
                next_value = next_value.replace("[", "") #? Removes open parentheses
                next_value = next_value.replace("]", "") #? Removes close parentheses

                debug(f"COMMAND : {next_value}")
                cmd_threads.append(threading.Thread(target=open_cmd, args=[next_value]))
                cmd_threads[-1].start()

            if end_of_system_command:
                next_value = ""


        else:
            print(response, end="", flush=True)
        
        if update_context and response_item["done"] == True: #?OPTIMIZATION REQUIRED
            current_context = response_item["context"]

def get_option(options: list[str], short_option: str, long_option: str) -> str:
    index = 0
    try:
        index = options.index(long_option)
    except ValueError:
        index = options.index(short_option)
        
    try:
        #? Update the configuration file
        index = options.index(short_option)
        return options[index+1]
    except IndexError:
        #? If the option is not complete
        print(f"please specify the configuration file or not using {short_option} or {long_option} at all :)")
        exit(0)


#? Check if there's ollama inside the machine
[output, code] = cmd("ollama --version")


#? If there's no ollama AI installed in current machine
if code != 0:
    print(f"I'm afraid that I can run, master :(")
    print(f"Please install ollama first :(")
    exit(0)


options = []
if len(sys.argv) > 0:
    options = list(sys.argv)

fast_startup = False #? If fast startup true, there's no delay when trying to start VAR
choosen_model = ""

if len(options) > 0:
    #? If the user specify the model
    if "--model" in options or "-m" in options:
        choosen_model = get_option(options, "-m", "--model")

    #? Listing ollama model
    if "--list-model" in options or "-l" in options:
        [output, code] = cmd("ollama list")
        print(f"{output}")
        exit(0)

    #? Specify configuration file path
    if "--config" in options or "-c" in options:
        configuration_file_path = get_option(options, "--config", "-c").replace("~", HOME)

    #? Fast startup mode
    if "--fast" in options or "-f" in options:
        fast_startup = True

    #? Change message folder
    if "--message-folder" in options or "-f" in options:
        message_folder_path = get_option(options, "-f", "--message-folder").replace("~", HOME)

    #? 
    if "--version" in options or "-v" in options:
        print(f"VAC (Virtual Arch Companion). ver: {VERSION}")
        exit(0)
        

# ----------------------------------------------- USER CONFIGURATION ----------------------------------------------- #
#? If the choosen model is empty.. Get the model from the configuration file
user_configurations = {}
try:
    with open(configuration_file_path, "r") as f:
        user_configurations = json.load(f)
except FileNotFoundError:
    pass

#? If model has not been specified by the user
if choosen_model == "":
    #? If in the user configuration there's no "model" specified.
    if "model" not in user_configurations:
        print("there's no model specified in the user configuration file.\nThe default configuration file path is in here: ~/.config/vac/config.json")
        exit(0)
        
    #? If there is, change it so it'll refrence to the config file
    else:
        choosen_model = user_configurations["model"]

if message_folder_path == "" and "message-folder-path" in user_configurations and user_configurations.get("message-folder-path") != "":
    message_folder_path = user_configurations.get("message-folder-path")

if message_folder_path == "":
    message_folder_path = f"/home/{os.getlogin()}/.var/vac/messages"

if "save-message-history" in user_configurations and user_configurations.get("save-message-history") != "":
    save_messages_history = user_configurations.get("save-message-history")

# ---------------------------------------------------------------------------------------------------------------- #

message_folder_path = message_folder_path if message_folder_path.endswith("/") else (message_folder_path+"/")

#? ====== Starting ollama service ===== ?#
[output, code] = cmd("ollama start")
print("Starting ollama on your computer...", end="\r")
time.sleep(0.5) if not fast_startup else print(end="")
#? If there's an error when starting ollama..
if output != 0:
    #? If the error is actually is already running so that we don't have to run it again
    if output == "Error: listen tcp 127.0.0.1:11434: bind: address already in use":
        print("oh.. it's already running.. aight", end="\r")
        time.sleep(1) if not fast_startup else print(end="")
        
    else:
        print_error("STARTING OLLAMA ERROR", output)
        exit(0)

print_success("STARTING OLLAMA SUCCESS", "....              ")

use_first_prompt = False
loaded_context = ""
#? ===== Prompt the first-prompt in config file ===== ?#
if "load-context" in user_configurations and user_configurations["load-context"] != "":
    loaded_context = user_configurations["load-context"]

elif "first-prompt" in user_configurations and user_configurations["first-prompt"] != "":
    use_first_prompt = True
    first_prompt = user_configurations["first-prompt"]
    print(first_prompt)
    result = send_req_to_ai(first_prompt, choosen_model)
    generate_response(result)


    


#? ====== Running the AI! ====== ?#
client_thread.start()
print("Waiting for command..")
while running:
    message = ""
    print(f"{RED_COLOR}[CHECKING..]") #? DEBUGGIN3
    for file in os.listdir(message_folder_path):
        if file.endswith(".vac") and file.startswith("message-"):
            file_path = message_folder_path + file
            message_file:io.TextIOWrapper = io.open(file_path, "r+")
            message = message_file.read()
            message_file.close()
            if save_messages_history:
                debug(f"mv '{message_file.name} {message_file.name[:-len(file)]}/history-{file}'")
                cmd(f"mv '{message_file.name} {message_file.name[:-len(file)]}/history-{file}'")
            else:
                debug(f"rm '{message_file.name}'")
                cmd(f"rm '{message_file.name}'")
            
    

    #? If there's a new message
    if message != "":
        print(f"{USER_TEXT_COLOR}[USER] {WHITE_COLOR}{message}")
        result = send_req_to_ai(message, choosen_model)
        print(f"{ARCH_TEXT_COLOR}[ARCH] {WHITE_COLOR}", end="")
        generate_response(result)
        print()
        afk_count = 0

    if wait_time < 1 and wait_time > -1:
        print(f"{AFK_TEXT_COLOR}[WAIT TIMEOUT] {WHITE_COLOR}", end="\n", flush=True)
        result = send_req_to_ai(f"[system:system_command] you've waited for the user but the user is not answered you or maybe he's currently afk or maybe he's currently typing..", choosen_model)
        print(f"{ARCH_TEXT_COLOR}[ARCH] {WHITE_COLOR}", end="", flush=True)
        generate_response(result)
        print()
        afk_count += 1
        
    wait_time -= 1
    time.sleep(1) #? In order to make it doesn't read too fast.
    

