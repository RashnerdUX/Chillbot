### Extra Information for Python Logging
Here's link for the explanation - (Click here)[https://g.co/gemini/share/ea25f3573d19]

## File Logging
There is a way to avoid the files getting too large. Either of the following handlers are preferred

- RotatingFileHandler: This opens a new file with the same name once a maximum size is reached e.g If limit is 3MB then when app.log gets to 3mb, it is renamed to "app.log.1" immediately and another "app.log" takes its place
- TimeBoundRotatingFileHandler: The files are rotated based on a time schedule

## Dynamic Log Levels
Once in a while, there might be need to debug the program and the debug logs are needed. An HTTP endpoint should be exposed that allows the team to change the debug level for the root application at any point in time thus allowing "DEBUG" prints to get printed to the console




