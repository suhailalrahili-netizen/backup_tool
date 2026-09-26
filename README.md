# Local Backup Utility — Project Documentation

## Introduction

This project is the begining from the problem that we face sometimes, we forget to make backup copy of the Project, like what happened at the ministry of health, becuase the system have a sudden failure and the data was lost because there is no updated backup.

Because of this, I think about this problem and decided to do a simple tool the solves the problem, a local tool with graphical user interface. It allow the user to perform backups manually or automatically.

## Goal of the Project

The goal from this project is give a fast and simple way to save important folders without need to complicated programs or online services. Also to reduce the human mistake of forgeting to make backup, by adding automatic schedule. And to make sure the backup file is not corrupted before telling to the user its done. And also give a way for restore the files back if something happen to the original folder.

## Tools and Technologies

I build this project using Python language, with tkinter library for the graphical interface. All the librarys i used is already built in python, i didn't need to install anything external:

| Library | What I used it for |
|---|---|
| `os` | for handle paths, check folders, delete old files |
| `threading` | to run the backup process in background so the interface dont freeze |
| `queue` | to send messages betwen the background thread and the interface safely |
| `zipfile` | to create the zip archive, check if its currupted, and extract it later |
| `datetime` / `time` | to generate unique name for every backup and calculate the time betwen automatic backups |
| `tkinter` | for build the whole interface, buttons, fields, progress bar |

## Features

### 1. Backup

The user choose a source folder and destination folder, and the program go through all the files inside it (even subfolders) and compress them into one zip file. The name of file is generated automatic using the date and time so every backup have a unique name. I also exclude some folder that is not important for backup like `.git` and `node_modules` because they are heavy and useless.

After the zip is created, the program check if the archive is corrupted before it say the backup is success, this way we make sure the backup is actually usable when we will need it.

### 2. Automatic Backup

I add a option for enable automatic backup every X minutes, the user choose the number. While the program is open, there is a loop that check every second if its time for make new backup, and if yes it will started automatically without the user do anything. This feature is the one who solve the "forgetting" problem i mention it in introduction.

The automatic backup only works while the program was open, this is a design desicion i made it to keep simple for now. In future it can connect to the operating system scheduler (Task Scheduler in windows or cron in linux) so it works even the program is closed.

### 3. Retention Policy

So the disk dont get full from old backups that is useless, the program keeps only last 3 backups automatically. Every time a new backup is succeed, it checks all the backups on the destination folder and delete the oldest one, keeping only the newest 3.

### 4. Restore

I also added the ability for restore files from any previous backup. The user select a zip file from the backups, and choose a folder for extract into it, then the program will extract the files there after ask confirmation from user (because restore can overwrite the existing files that have same name).

While I building this feature i learned about a security problem called Zip Slip, where a file inside the archive can has a path that try to write it outside the folder that was choosen for restore. So i added a check that make sure every file is going to its correct place inside the selected folder only, and any file who try escape from this is skipped.

## How It Works (Internal Logic)

The most important technical desicion in this project was how keeping the interface responsive while doing a long operation like compress many files. If i run this operation on same thread like the interface, the window will freeze and it dont respond for the user until the operation is finish.

The solution i used it: any backup or restore operation is running on a separate thread from the interface. But because a separate thread cant updates the interface directly (its not safe), i used a queue like a middle man between them: the thread put messages inside the queue (progress, log, success, or error), and the interface checking the queue every small amount of time and updates itself depend on the messages it recieves.

This design is what allowed me for add the three extra features (scheduling, retention, restore) without touch the interface logic, because everything is following same pattern: background operation is sending messages, interface just recieve and display it.

## How to Run

This is the steps for run the project on your computer:

1. Make sure you have Python installed on your device (I used Python version 3, any version 3.x should work fine).
2. Download the project file `backup_tool.py` and put it on any folder you want.
3. Open a terminal (or cmd) and go to the folder where the file is, using `cd` command.
4. Run this command:
   ```
   python backup_tool.py
   ```
   or if that dont work, try:
   ```
   python3 backup_tool.py
   ```
5. The program window will open automatically. You dont need to install any extra library, because `tkinter` and all the other librarys is already built in with python.
6. Choose the Source Folder (the folder you want to backup) and the Destination Folder (where you want to save the zip file), then press "Start Backup".
7. If you want the automatic backup, check the box "Enable automatic backup every" and write the number of minutes, and keep the program open.
8. To restore files, press "Restore Backup...", choose the zip file, then choose the folder you want to extract the files into it.

**Note:** the program dont need internet connection, everything works locally on your device.

## Challenges I Faced

- Interface was freezing during compress operation — solved by using separate Thread
- Update the interface safely from another thread — solved by using Queue instead direct update
- Preventing conflict betwen backup and restore that running at same time — solved with a busy state variable who disable both buttons while any operation is running
- Making sure restore operation are safe from external archives — solved by checking of Zip Slip before extract any file

## Future Improvements

- Connect the automatic schedule with the operating system so it works even the program was closed
- Add incremental backup instead compressing all files every time
- Add optional password encryption for the archive, for the sensitive files
- Show a history log for all previous backup instead just the current operation

## Conclusion

This project is started as a simple idea for solve a daily problem that me and probably many peoples face it, forgeting to make backups for important files. It become a complete tool with backup, automatic scheduling, retention policy and restore, all built by using Python without any external library. The thing i learned it most from this project is how handling operations that take time inside a graphical interface without freezing it, and this is a concept i will definitly use it in future projects.