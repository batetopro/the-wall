# the-wall

  ![swagger](https://github.com/batetopro/the-wall/raw/main/assets/swagger.png)


## Description 
The description of the problem solved with this project can be found 
[here](https://github.com/batetopro/the-wall/raw/main/assets/The%20Wall.pdf)

## Installation
Git clone the repository
```commandline
git clone git@github.com:batetopro/the-wall.git
```
After that, go to the folder, in which the repository was cloned.
```commandline
cd the-wall
```
Optionally, create a new virtualenv:
```commandline
python -m venv .venv
source .venv/bin/activate
```
Install the requirements:
```commandline
pip isntall -r requirements.txt
```
Run the tests:
```commandline
python wall/manage.py test
```
Start the server:
```commandline
python wall/manage.py runserver
```
When starting the server, a log of the wall building process can be observed.

## Configuration
The process of wall building can be configured by using environment variables:
* IS_MULTI_THREADED - mode of wall building process.
* THREADS_NUMBER - number of workers to build the wall.
* WALL_FILE - initial profiles of the wall.

## History contents
Below is a class diagram of the history pacakge.

  ![class_diagram](https://github.com/batetopro/the-wall/raw/main/assets/class_diagram.png)

The classes of the package are:
* History - represents the build history.
* HistoryBuilder - abstract builder of History.profiles
* SimpleHistoryBuilder - builder of History.profiles, 
which builds all profiles at once oer day.
* MultiThreadedHistoryBuilder - builder of History.profiles, which uses workers to build profiles.
* BuilderThread - workers of MultiThreadedHistoryBuilder - build one profile section.
