# SPET Project
Electrical playing propulsion demo

### How do I get set up? ###

1. install python3.9^
2. activate virtual environment: 
    ```shell
    python -m venv .venv
    ```
   (i.e. "python" schould be the path of your python3.exe file)
3. select local .venv as interpreter of the project
4. install poetry: 
    ```shell
    (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
    ```
    or in mac:
    ```shell
    curl -sSL https://install.python-poetry.org | python3 -
    ```
5. install  required packages: 
    ```shell 
    poetry install
    ```
