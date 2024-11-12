#!
# Setup configuration file
continue_write="Y"

if [ -d ~/.config/vac ]; then
    continue_write="n"
    printf "~/.config/vac directory is already found. \e[0;31mRewrite the folder?\e[0;37m"
    read continue_write
fi

if [ "$continue_write" == "Y" -o "$continue_write" == "y" ]; then
    printf "Writing to ~/.config/vac/..."
    mkdir ~/.config/vac/
    touch ~/.config/vac/config.json
    printf '{\n	"model": "arch-anime-assistant",\n	"allow-command-prompt": true,\n	"confirmation-command-prompt": true,\n	"first-prompt": "",	\n	"activate-memory": true,\n	"max-output-words": 0,\n	"save-message-history":false,\n	"debug-file-path": "~/.var/vac/debug.log",\n	"message-folder-path": "~/.var/vac/messages",\n	"sounds-folder-path": "$FILE_PATH/Sounds",\n	"memory-file-path": "~/Documents/VAC/memory.json"\n}' > ~/.config/vac/config.json
fi

# Setup logging and chat file
continue_write="Y"
if [ -d ~/.var/vac ]; then
    continue_write="n"
    printf "~/.var/vac directory is already found. \e[0;31mRewrite the folder?\e[0;37m"
    read continue_write
fi

if [ "$continue_write" == "Y" -o "$continue_write" == "y" ]; then
    printf "Writing to ~/.var/vac/..."
    mkdir ~/.var/vac
    mkdir ~/.var/vac/messages
    touch ~/.var/vac/debug.log
fi
    

# Setup ollama
if ! ollama -v  2>&1 >/dev/null
then
    printf "ollama could not be found.. want to install it with 'curl -fsSL https://ollama.com/install.sh | sh'?"

    install_ollama=""
    read install_ollama

    if [ "$install_ollama" == "Y" -o "$install_ollama" == "y" ]; then
        curl -fsSL https://ollama.com/install.sh | sh
    else
        exit 0
    fi
fi
ollama pull llama3.1:8b
ollama create arch-anime-assistant -f arch-anime-assistant

# Setup .bashrc
setup_environment=""
printf "Want to setup for the variable environment? (Y/n) "
read setup_environment
if [ "$setup_environment" == 'Y' -o "$setup_environment" == 'y' ]; then
    is_using_bashrc=""
    printf "Are you using bashrc? (Y/n)"
    read is_using_bashrc
    
    if [ "$is_using_bashrc" == "Y" -o "$is_using_bashrc" == "y" ]; then
        printf "\n\nexport PATH=${PWD}/:\$PATH" >> ~/.bashrc
    else
        is_using_zsh=""
        printf "Are you using zsh? (Y/n)"
        read is_using_zsh
        if [ "$is_using_zsh" == "Y" -o "$is_using_zsh" == "y" ]; then
            printf "\n\nexport PATH=${PWD}/:\$PATH" >> ~/.zshrc
        else
            shell_configuration_file=""
            printf "Specify the location of your shell configuration file: "
            read shell_configuration_file
            # Expand the path if it starts with '~'
            shell_configuration_file=$(eval echo "$shell_configuration_file")
            printf "\n\nexport PATH=${PWD}/:\$PATH" >> "$shell_configuration_file"
        fi
    fi
fi

# DONE!
printf "\033[0;32msetup successfully exited!\033[0;37m\n"
printf "you can change configuration at:~/.config/vac/config.json\n"

