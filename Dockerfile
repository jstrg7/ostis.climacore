FROM ubuntu:noble AS base

ENV CCACHE_DIR=/ccache
USER root

COPY scripts /example-app/scripts
COPY conanfile.py /example-app/conanfile.py
COPY CMakePresets.json /example-app/CMakePresets.json
COPY CMakeLists.txt /example-app/CMakeLists.txt
COPY requirements.txt /example-app/requirements.txt

# tini is an init system to forward interrupt signals properly
RUN apt update && apt install -y --no-install-recommends sudo tini curl ccache python3 python3-pip pipx cmake build-essential ninja-build

# Install Conan
RUN pipx install conan && \
    pipx ensurepath

FROM base AS devdeps
WORKDIR /example-app

SHELL ["/bin/bash", "-c"]
RUN python3 -m venv /example-app/.venv && \
    source /example-app/.venv/bin/activate && \
    pip3 install -r /example-app/requirements.txt

ENV PATH="/root/.local/bin:$PATH"
RUN conan remote add ostis-ai https://conan.ostis.net/artifactory/api/conan/ostis-ai-library && \
    conan profile detect && \
    conan install . --build=missing

# Install sc-machine binaries
RUN ./scripts/install_cxx_problem_solver.sh

FROM devdeps AS devcontainer
RUN apt install -y --no-install-recommends cppcheck valgrind gdb bash-completion ninja-build curl
ENTRYPOINT ["/bin/bash"]

FROM devdeps AS builder
COPY . .
RUN --mount=type=cache,target=/ccache/ cmake --preset release-conan && cmake --build --preset release

# Gathering all artifacts together
FROM base AS final

COPY --from=builder /example-app/scripts /example-app/scripts
COPY --from=builder /example-app/install /example-app/install
COPY --from=builder /example-app/build/Release/extensions /example-app/build/Release/extensions
COPY --from=builder /example-app/.venv /example-app/.venv

WORKDIR /example-app

EXPOSE 8090

ENTRYPOINT ["/usr/bin/tini", "--", "/example-app/scripts/docker_entrypoint.sh"]
