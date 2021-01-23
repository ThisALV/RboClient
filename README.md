# RboClient

Cross-platform client for [RpgBookOnline](https://github.com/ThisALV/RpgBookOnline#the-rbo-project), an online role-play editor and game.

To learn more about the Rbo project, a game for creating and playing classic role-plays online, click [here](https://github.com/ThisALV/RpgBookOnline#the-rbo-project).

[Get the Rbo server](https://github.com/ThisALV/RpgBookOnline)

[Get familiar with the gameplay and/or the interface](https://github.com/ThisALV/RpgBookOnline/wiki)

## Table of contents

   * [RboClient](#rboclient)
      * [Table of contents](#table-of-contents)
      * [Install](#install)
         * [Prerequisites](#prerequisites)
            * [Git](#git)
            * [Python interpreter](#python-interpreter)
            * [Kivy (GUI library)](#kivy-gui-library)
            * [Twisted (networking library)](#twisted-networking-library)
         * [Steps](#steps)
      * [Quick and Easy install (For Windows)](#quick-and-easy-install-for-windows)
      * [Run](#run)


## Install

### Prerequisites

#### Git

```shell
sudo apt install git
```

For Windows users : https://git-scm.com/download/win

#### Python interpreter

The installed Python interpreter version might be from 3.6 to 3.9 *included*.

```shell
sudo apt install python3 
```

For Windows users : https://www.python.org/downloads/windows/

#### Kivy (GUI library)

To get the Kivy package, you must have a C/C++ compiler installed. On Linux distributions, you should have one by default, but for Windows, you must either have Visual Studio IDE installed or follow the instructions on [this link](https://github.com/kivy/kivy/wiki/Using-Visual-C---Build-Tools-instead-of-Visual-Studio-on-Windows) if you really don't want to install the full IDE.

Once you are sure to have an available compiler on your system can run the following command :

```shell
python -m pip3 install Kivy
```

#### Twisted (networking library)

Then you have to get Twisted package. Just enter this command :

```shell
python -m pip3 install Twisted
```

### Steps

Just clone this repository with `git clone https://github.com/ThisALV/RboClient`.

## Quick and Easy install (For Windows)

*Comming soon...*

## Run

Enter the cloned repo directory and type `python main.py` to start the client.

If config.ini file is corrupted, simply delete it to make to repair the client.
