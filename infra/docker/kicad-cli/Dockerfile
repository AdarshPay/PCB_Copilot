# Thin PCB Copilot wrapper around the official KiCad CLI image.
# Primary use: `kicad-cli sch erc` / `kicad-cli pcb drc` in CI and worker jobs.
#
# Build:
#   docker build -t pcb-ai-kicad-cli:local -f infra/docker/kicad-cli/Dockerfile infra/docker/kicad-cli
#
# See README.md in this directory for ERC invocation examples.

ARG KICAD_TAG=10.0
FROM kicad/kicad:${KICAD_TAG}

LABEL org.opencontainers.image.title="pcb-ai-kicad-cli"
LABEL org.opencontainers.image.description="KiCad CLI image for PCB Copilot native ERC/DRC verification"
LABEL org.opencontainers.image.source="https://github.com/local/PCB_Copilot"

WORKDIR /work

# Official image already provides ENTRYPOINT ["kicad-cli"]; keep that contract.
# Default CMD shows help when the container is started with no arguments.
CMD ["--help"]
