#!/bin/bash

# Check if pyenv is installed
if ! command -v pyenv &> /dev/null; then
    echo "pyenv is not installed. Please install pyenv first."
    exit 1
fi

# Get the latest Python version available in pyenv
LATEST_PYTHON=$(pyenv install --list | grep -v - | grep -v b | tail -1 | xargs)

# Install the latest Python version if not already installed
if ! pyenv versions | grep -q $LATEST_PYTHON; then
    echo "Installing Python $LATEST_PYTHON..."
    pyenv install $LATEST_PYTHON
fi

# Set the virtual environment name
VENV_NAME=".venv"

# Check if the virtual environment already exists in the current directory
if [ -d "$VENV_NAME" ]; then
    echo "Virtual environment '$VENV_NAME' already exists in the current directory."
else
    echo "Creating virtual environment '$VENV_NAME' in the current directory..."
    pyenv virtualenv $LATEST_PYTHON $(basename $(pwd))-$VENV_NAME
    ln -s $(pyenv prefix $(basename $(pwd))-$VENV_NAME) $VENV_NAME
fi

# Set the local Python version to the new virtual environment
pyenv local $(basename $(pwd))-$VENV_NAME

# Activate the virtual environment
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

echo "Virtual environment '$VENV_NAME' created and activated using Python $LATEST_PYTHON"
echo "Python version:"
python --version
echo "Python path:"
which python