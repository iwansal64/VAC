import os, subprocess, sys, json, time, ollama, threading, datetime
from typing import Tuple, Mapping, Iterator

RED_COLOR = "\033[0;31m"
GREEN_COLOR = "\033[0;32m"
WHITE_COLOR = "\033[0;37m"
GREEN_BOLD_COLOR = "\033[1;32m"
BLUE_BOLD_COLOR = "\033[1;34m"
YELLOW_BOLD_COLOR = "\033[1;33m"
USER_COLOR = GREEN_BOLD_COLOR
ARCH_COLOR = BLUE_BOLD_COLOR
AFK_COLOR = YELLOW_BOLD_COLOR

#? Used to synchronize the AI side to the USER side
running = True

#? Used to keep track of context
current_context = []

#? Used to make the AI talk to the user wherever the wait time is up
wait_time = -1

#? Configration file path... You can change it if you want to make it permanently change :)
configuration_file_path = f"/home/{os.getlogin()}/.config/vac/config.json"
#? Message file path
message_file_path = f"/home/{os.getlogin()}/.config/vac/virtual-arch-message.txt"

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

def open_user_side():
    '''
    Open the client side in new window
    '''
    global running

    cmd("kitty sh ./open_user_side.sh & disown")
    running = False


client_thread = threading.Thread(target=open_user_side)
client_thread.start()

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
    next_wait_time = ""
    for response_item in response_iterator:
        response = response_item.get("response")
        if "[" in response or next_wait_time != "":
            next_wait_time += response
            
            if next_wait_time.startswith("[wt:") and "]" in next_wait_time:
                debug(f"BEFORE:{next_wait_time}")
                next_wait_time = next_wait_time.replace(" ", "") #? Removes spaces
                next_wait_time = next_wait_time.replace("wt", "") #? Removes 'wt'
                next_wait_time = next_wait_time.replace(":", "") #? Removes ':'
                next_wait_time = next_wait_time.replace("[", "") #? Removes open parentheses
                next_wait_time = next_wait_time.replace("]", "") #? Removes close parentheses
                debug(f"AFTER:{next_wait_time}")

                if next_wait_time == "N/A":
                    wait_time = -1
                else:
                    try:
                        wait_time = int(next_wait_time)
                        debug(f"wait_time ({next_wait_time}) is a number")
                    except ValueError:
                        debug(f"wait_time ({next_wait_time}) is not a number")

                next_wait_time = ""

        print(response, end="", flush=True)
        
        if update_context and response_item["done"] == True: #?OPTIMIZATION REQUIRED
            current_context = response_item["context"]




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
        index = 0
        try:
            index = options.index("--model") 
        except ValueError:
            index = options.index("-m")
            
        try:
            #? Update the choosen model
            choosen_model = options[index+1]
        except IndexError:
            #? If the option is not complete!
            print("please specify the model or not using -m or --model at all :)")

    #? Listing ollama model
    elif "--list-model" in options or "-l" in options:
        [output, code] = cmd("ollama list")
        print(f"{output}")
        exit(0)

    #? Specify configuration file path
    elif "--config" in options or "-c" in options:
        index = 0
        try:
            index = options.index("--config") 
        except ValueError:
            index = options.index("-c")
            
        try:
            #? Update the configuration file
            index = options.index("-c")
            configuration_file_path = options[index+1]
        except IndexError:
            #? If the option is not complete
            print("please specify the configuration file or not using -c or --config at all :)")

    #? Fast startup mode
    elif "--fast" in options or "-f" in options:
        fast_startup = True


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

if "message-file-path" in user_configurations:
    message_file_path = user_configurations.get("message-file-path")

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


    


#? ====== Load the profile if there's load-profile in the config file ====== ?#
print("Waiting for command..")
while running:
    message_file = open(message_file_path, "r+")
    message = message_file.read()
    message_file.close()

    #? If there's a new message
    if message != "":
        print(f"{USER_COLOR}[USER] {WHITE_COLOR}{message}")
        result = send_req_to_ai(message, choosen_model)
        print(f"{ARCH_COLOR}[ARCH] {WHITE_COLOR}", end="")
        generate_response(result)
        print()
        
        with open(message_file_path, "w") as f:
            f.write("")

    if wait_time < 1 and wait_time > -1:
        result = send_req_to_ai(f"[system:system_command] you've waited for the user but the user is not answered you or maybe he's currently afk or maybe he's currently typing..", choosen_model)
        print(f"{ARCH_COLOR}[ARCH] {WHITE_COLOR}", end="")
        generate_response(result)
        print()
        
    wait_time -= 1
    time.sleep(1) #? In order to make it doesn't read too fast.
    

