# !pip install playsound
import os, subprocess, sys, json, time, ollama, threading, datetime, io, playsound3 as playsound
from typing import Tuple, Mapping, Iterator

CURRENT_DIR = "/".join(__file__.split("/")[:-1])

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
message_folder_path = "{HOME}/.var/vac/messages"

#? Memory file path
memory_file_path = f"{CURRENT_DIR}/memory.json"

#? Sound folder path
sounds_folder_path = "{CURRENT_DIR}/Sounds"

#? Save messages history
save_messages_history = False

#? Allow command prompt
allow_command_prompt = True

#? Confirmation command prompt
confirmation_command_prompt = True

#? Maximum number of words the AI can output
max_output_words = 0

#? Activate memory
activate_memory = True

#? Allowing the AI to send message while AFK
allow_wait = True

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
    global confirmation_command_prompt
    cmd(f"kitty sh ./open_cmd.sh '{command}' '{confirmation_command_prompt}' & disown")
    del cmd_threads[-1]

def open_user_side() -> None:
    '''
    Open the user side in new window
    '''
    global running

    cmd("kitty sh ./open_user_side.sh & disown")
    running = False


client_thread = threading.Thread(target=open_user_side)

def update_memory():
    '''
    Function that used to update the memory of AI
    '''
    global current_context
    
    with open(memory_file_path, "w") as memory_file:
        json.dump({
            "context": current_context,
            "time": time.time()
        }, memory_file)

def debug(message:str):
    '''
    Function that used to log a debug to the debug file path
    '''
    if "debug-file-path" in user_configurations and user_configurations.get("debug-file-path") != "":
        with open(user_configurations.get("debug-file-path"), "a+") as f:
            f.write(f"[{datetime.datetime.now().strftime(r'%d/%m/%Y %H:%M:%S')}]{message}\n")

def send_req_to_ai(command: str, model: str) -> Iterator[Mapping[str, str]]:
    '''
    Function that used to send prompt to the AI and get the result
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
    Used to generating response. response_iterator is should be the result of `ollama.generate(stream=True)` function
    '''
    global wait_time
    global current_context
    global afk_count
    
    next_value = ""
    is_processing = False
    
    for response_item in response_iterator:
        response = response_item.get("response")
        if not is_processing:
            playsound.playsound(sounds_folder_path+"/reply-notification.wav")
            is_processing = True

        if "[" in response or next_value != "":
            debug(response)
            next_value += response
            
            end_of_system_command = "]" in next_value
            if end_of_system_command:
                debug(next_value)
                debug("END OF SYSTEM COMMAND")

            #? Maximum amount of auto chat is 2
            if afk_count + 1 < 2 and next_value.replace(" ", "").startswith("[wt:") and end_of_system_command:
                next_value = next_value[next_value.index("["):]
                next_value = next_value.replace(" ", "") #? Removes spaces
                next_value = next_value.replace("wt", "") #? Removes 'wt'
                next_value = next_value.replace(":", "") #? Removes ':'
                next_value = next_value.replace("[", "") #? Removes open parentheses
                next_value = next_value.replace("]", "") #? Removes close parentheses

                if next_value == "N/A":
                    wait_time = -1
                elif allow_wait:
                    try:
                        wait_time = min(10, int(next_value)) * 2 #? Constrain the wait time to the minimal value of 10 seconds * 2 which is 20 seconds
                        debug(f"wait_time ({next_value}) is a number")
                    except ValueError:
                        debug(f"wait_time ({next_value}) is not a number")

            if allow_command_prompt:
                if next_value.replace(" ", "").startswith("[cmd:") and end_of_system_command:
                    next_value = next_value[next_value.index("["):next_value.index("]")]
                    next_value = next_value.replace("cmd", "") #? Removes 'cmd'
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
    '''
    Get the value of the option that given by the user
    '''
    index = 0
    try:
        index = options.index(long_option)
    except ValueError:
        index = options.index(short_option)
        
    try:
        index = options.index(short_option)
        return options[index+1]
    except IndexError:
        #? If the option doesn't include the value
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
configuration_file_path = configuration_file_path.replace("~", HOME)
user_configurations = {}
try:
    with open(configuration_file_path, "r") as f:
        user_configurations = json.load(f)
        for configuration in user_configurations:
            if "path" in configuration:
                user_configurations[configuration] = user_configurations[configuration].replace("~", HOME)
                
                if "$FILE_PATH" in user_configurations[configuration]:
                    user_configurations[configuration] = user_configurations[configuration].replace("$FILE_PATH", CURRENT_DIR)
                
except FileNotFoundError:
    pass

check_configuration = lambda configuration: configuration in user_configurations and user_configurations.get(configuration) != ""

#? If model has not been specified by the user
if choosen_model == "":
    #? If in the user configuration there's no "model" specified.
    if "model" not in user_configurations:
        print("there's no model specified in the user configuration file.\nThe default configuration file path is in here: ~/.config/vac/config.json")
        exit(0)
        
    #? If there is, change it so it'll refrence to the config file
    else:
        choosen_model = user_configurations["model"]

if check_configuration("message-folder-path"):
    message_folder_path = user_configurations.get("message-folder-path")

if message_folder_path == "":
    message_folder_path = f"/home/{os.getlogin()}/.var/vac/messages"

if check_configuration("save-message-history"):
    save_messages_history = user_configurations.get("save-message-history")

if check_configuration("sounds-folder-path"):
    sounds_folder_path = user_configurations.get("sounds-folder-path")

if check_configuration("allow-command-prompt"):
    allow_command_prompt = user_configurations.get("allow-command-prompt")

if check_configuration("confirmation-command-prompt"):
    confirmation_command_prompt = user_configurations.get("confirmation-command-prompt")

if check_configuration("activate-memory"):
    activate_memory = user_configurations.get("activate-memory")

if check_configuration("memory-file-path"):
    memory_file_path = user_configurations.get("memory-file-path")

if check_configuration("max-output-words"):
    max_output_words = user_configurations.get("max-output-words")

if check_configuration("allow-wait"):
    allow_wait = user_configurations.get("allow-wait")


# ---------------------------------------------------------------------------------------------------------------- #

# ---------------------------------------------- RETRIEVE MEMORY --------------------------------------------------#

last_time = 0
if activate_memory:
    try:
        with open(memory_file_path, "r") as f:
            saved_memory = json.load(f)
            try:
                last_time = saved_memory["time"]
                current_context = saved_memory["context"]
            except KeyError:
                pass

    except FileNotFoundError:
        pass

    
#? Retrieve time memory
seconds = round(time.time() - last_time)
minutes = 0
hours = 0
days = 0

while seconds >= 60:
    seconds -= 60
    minutes += 1

while minutes >= 60:
    minutes -= 60
    hours += 1

while hours >= 24:
    hours -= 24
    days += 1
    
# ---------------------------------------------------------------------------------------------------------------- #

message_folder_path = message_folder_path if message_folder_path.endswith("/") else (message_folder_path+"/")
message_folder_path = message_folder_path.replace("~", HOME)

#? ====== Starting ollama service ===== ?#
[output, code] = cmd("ollama start")
print("Starting ollama on your computer...", end="\r")
time.sleep(0.5) if not fast_startup else print(end="")
#? If there's an error when starting ollama..
if code != 0:
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
client_thread.start()
cmd("reset")
give_time_memory = True
#? ===== Prompt the first-prompt in config file ===== ?#
if "load-context" in user_configurations and user_configurations["load-context"] != "":
    loaded_context = user_configurations["load-context"]

elif "first-prompt" in user_configurations and user_configurations["first-prompt"] != "":
    use_first_prompt = True

    first_prompt = (f"(It's been {f'{days} days, ' if days > 0 else ''}{f'{hours} hours, ' if hours > 0 else ''}{f'{minutes} minutes, and ' if minutes > 0 else ''}{seconds} seconds since last time you talk to him)" if last_time != 0 else "")+user_configurations["first-prompt"]
    use_first_prompt = False
    print(f"{USER_TEXT_COLOR}[FIRST PROMPT USER]{WHITE_COLOR} {first_prompt}")
    result = send_req_to_ai(first_prompt, choosen_model)
    print(f"{ARCH_TEXT_COLOR}[ARCH] {WHITE_COLOR}", end="", flush=True)
    generate_response(result)


    


#? ====== Running the AI! ====== ?#
print("Waiting for command..")
while running:
    message = ""
    # print(f"{RED_COLOR}[CHECKING..]") #? DEBUGGING
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
        result = send_req_to_ai(f"{f'(From now on you are limited to {max_output_words} words each response)' if max_output_words else ''}(It's been {f'{days} days,' if days > 0 else ''}{f'{hours} hours,' if hours > 0 else ''}{f'{minutes} minutes,' if minutes > 0 else ''}{seconds} seconds since the last time you met him)"+message if give_time_memory else message, choosen_model)
        print(f"{ARCH_TEXT_COLOR}[ARCH] {WHITE_COLOR}", end="")
        generate_response(result)
        print()

        if activate_memory:
            update_memory()
            
        if give_time_memory:
            give_time_memory = False
        afk_count = 0

    #? If the wait_time is timeout
    if allow_wait and (wait_time < 1 and wait_time > -1):
        print(f"{AFK_TEXT_COLOR}[WAIT TIMEOUT] {WHITE_COLOR}", end="\n", flush=True)
        result = send_req_to_ai(f"[system:system_command] you've waited for the user but the user is not answered you or maybe he's currently afk or maybe he's currently typing..", choosen_model)
        print(f"{ARCH_TEXT_COLOR}[ARCH] {WHITE_COLOR}", end="", flush=True)
        generate_response(result)
        print()
        afk_count += 1
        wait_time -= 3
        
    wait_time -= 1
    time.sleep(1) #? In order to make it doesn't read too fast.
    

