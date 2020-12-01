# ichi bot source

## Requirements
Running the .exe doesn't have requirements, just download it, the config and db files in a single folder and run. Don't forget to edit the config file
- [Python 3.8.6](https://www.python.org/downloads/release/python-386/)
- [Tomer's Unofficial kik bot api library](https://travis-ci.org/joemccann/dillinger.svg?branch=master)
- [Intellivoid's Coffeehouse python library](https://github.com/intellivoid/CoffeeHouse-Python-API-Wrapper)

## Setting up
Check the config.ini file

## Important
Make sure to run a command using a pass as soon as the bot is up so that it changes

## Instructions & usage
The help message is saved in 'help.txt'  
The current pass is saved in 'passkey.txt', it changes every time it is used, using the 'pass' command will send it to you, if you are in the 'super' list

### Commands

'ping' pong!  
'help' sends the help message  
'count' sends the saved group count  
'pass' sends the current passkey, assuming you are in the 'super' list  
'settings' sends the current group settings  
'admins' sends the detected admins  
'welcome'/'rules' sends the welcome message  
'welcome (welcome message)' sets the welcome message  
'delete welcome' deletes the welcome message  
'days (number)' kicks accounts that are less than (number) days old, set to 0 to disable  
'reset' erases group data and leaves  
'quit' leaves without erasing group data  
'lock' locks the group  
'unlock' unlocks the group  
'enable AI' enables Coffeehouse AI  
'disable AI' disables Coffeehouse AI  
'dgg (query)' searches a duckduckgo query   

(all commands are excluding the parentheses)

### That's it, enjoy the bot
