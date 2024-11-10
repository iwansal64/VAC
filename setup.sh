# Setup configuration file
mkdir ~/.config/vac/
touch ~/.config/vac/config.json
printf '{\n	"model": "arch-anime-assistant",\n	"allow-background": true,\n	"first-prompt": "",	\n	"load-context": "",\n	"max-output-words": 0,\n	"save-message-history":false,\n	"message-file-path": "~/.config/vac/virtual-arch-message.txt",\n	"debug-file-path": "~/.var/vac/debug.log",\n	"message-folder-path": "~/.var/vac/messages"\n}' > ~/.config/vac/config.json

# Setup logging and chat file
mkdir ~/.var/vac
mkdir ~/.var/vac/messages
touch ~/.var/vac/debug.log

# Setup ollama
if ! ollama -v  2>&1 >/dev/null
then
    printf "<the_command> could not be found\n"
    exit 1
fi
ollama pull llama3.1:8b
ollama create arch-anime-assistant -f arch-anime-assistant

# Setup .bashrc
setup_environment=""
printf "Want to setup for the variable environment? (Y/n) "
read setup_environment
if [ "$setup_environment" == 'Y' -o "$setup_environment" == 'y' ]; then
    is_using_bashrc = ""
    printf "Are you using bashrc? (Y/n)"
    read is_using_bashrc
    
    if [ "$is_using_bashrc" == "Y" -o "$is_using_bashrc" == "y" ]; then
        printf "\n\nexport PATH=/home/ridwan/Codes/Python/VAC/:\$PATH" >> ~/.bashrc
    else
        printf "\n\nexport PATH=/home/ridwan/Codes/Python/VAC/:\$PATH" >> ~/.zshrc
    fi
fi

# DONE!
printf "\033[0;32msetup successfully exited!\033[0;37m\n"
printf "you can change configuration at:~/.config/vac/config.json\n"

