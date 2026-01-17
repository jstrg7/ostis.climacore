<h1 align="center">ostis.climacore</h1>

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⚠️ **Note**: This project is part of the **OSTIS Technology** ecosystem and utilizes its components. All source software, tools, and architecture belong to the [OSTIS](https://github.com/ostis-ai) project.

## Overview

**ostis.climacore** is a working application for climate management using semantic technologies, built on top of [OSTIS Technology](https://github.com/ostis-ai).

## Getting Started

Native installation is required.

### Prerequisites

Ensure the following tools are installed:

#### General Prerequisites

*   **Git:** for cloning the repository.  
    [Git Installation Instructions](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)

## Installation (Native Build)

Steps to install and run the application directly on your system.

1.  **Install basic development environment tools:**

    *   **Ubuntu/Debian (GCC):**
        ```sh
        sudo apt update
        sudo apt install --yes --no-install-recommends \
            curl \
            ccache \
            python3 \
            python3-pip \
            build-essential \
            ninja-build
        ```

    *   **macOS (Clang):**
        ```sh
        brew update && brew upgrade
        brew install \
            curl \
            ccache \
            cmake \
            ninja
        ```

    *   **Other Linux Distributions:**
        Ensure equivalent packages are installed:
        *   `curl` — a tool for transferring data;
        *   `ccache` — a compiler cache to speed up builds;
        *   `python3` and `python3-pip` — Python 3 interpreter and package manager;
        *   `build-essential` (or equivalent) — includes a C++ compiler;
        *   `ninja-build` — a fast build system.

2.  **Install pipx:**

    Follow the instructions: [https://pipx.pypa.io/stable/installation/](https://pipx.pypa.io/stable/installation/).  
    `pipx` isolates Python packages and prevents conflicts.

3.  **Install CMake via pipx:**
    ```sh
    pipx install cmake
    pipx ensurepath
    ```

4.  **Install Conan via pipx:**
    ```sh
    pipx install conan
    pipx ensurepath
    ```

5.  **Clone the repository:**
    ```sh
    git clone --recursive https://github.com/jstrg7/ostis.climacore.git
    ```

6.  **Restart your shell:**
    ```sh
    exec $SHELL
    ```

7.  **Install C++ problem solver dependencies:**
    ```sh
    conan remote add ostis-ai https://conan.ostis.net/artifactory/api/conan/ostis-ai-library
    conan profile detect
    conan install . --build=missing
    ```

8.  **Install sc-machine and scl-machine binaries:**
    ```sh
    ./scripts/install_cxx_problem_solver.sh
    ```

9.  **Install sc-web (web interface):**

    *   **Ubuntu/Debian:**
        ```sh
        cd interface/sc-web
        ./scripts/install_deps_ubuntu.sh
        npm install
        npm run build
        cd ../..
        ```

    *   **macOS:**
        ```sh
        cd interface/sc-web
        ./scripts/install_deps_macOS.sh
        npm install
        npm run build
        cd ../..
        ```

## Building the OSTIS System

1.  **Build the problem solver (C++ agents):**
    ```sh
    cmake --preset release-conan
    cmake --build --preset release
    ```

2.  **Build the knowledge base:**
    ```sh
    ./scripts/start.sh build_kb
    ```

## Running the OSTIS System

1.  **Start `sc-machine` (in one terminal):**
    ```sh
    ./scripts/start.sh machine
    ```

2.  **Start `sc-web` (in another terminal):**
    ```sh
    ./scripts/start.sh web
    ```

3.  **Open in your browser:** [http://localhost:8000](http://localhost:8000)

    ![Example interface](https://i.imgur.com/6SehI5s.png)

Press `Ctrl+C` in both terminals to stop.