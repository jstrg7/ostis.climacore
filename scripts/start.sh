#!/usr/bin/env bash
set -eo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT_PATH="$(cd "$SCRIPT_PATH/.." && pwd)"

SC_MACHINE_PATH="$PROJECT_ROOT_PATH"/install/sc-machine
PS_COMMON_LIB_PATH="$PROJECT_ROOT_PATH"/install/ps-common-lib/
SCP_MACHINE_PATH="$PROJECT_ROOT_PATH"/install/scp-machine
SCL_MACHINE_PATH="$PROJECT_ROOT_PATH"/install/scl-machine
FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE="$PROJECT_ROOT_PATH"/install/fixed-search-strategy-template-processing-module

LD_LIBRARY_PATH="$LD_LIBRARY_PATH/lib:$SC_MACHINE_PATH/lib:$PS_COMMON_LIB_PATH/lib:$SCL_MACHINE_PATH/lib:$LD_LIBRARY_PATH"

case "$1" in
  build_kb)
    "$PROJECT_ROOT_PATH"/install/sc-machine/bin/sc-builder -i repo.path -o kb.bin --clear
    ;;
  machine)
    LD_LIBRARY_PATH="$LD_LIBRARY_PATH" \
      $SC_MACHINE_PATH/bin/sc-machine -s kb.bin \
      -e "$SC_MACHINE_PATH/lib/extensions;$SCP_MACHINE_PATH/lib/extensions;$SCL_MACHINE_PATH/lib/extensions;$FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_MODULE/lib/extensions;$PROJECT_ROOT_PATH/build/Release/extensions" -c ostis-example-app.ini
    ;;
  web)
    cd $PROJECT_ROOT_PATH/interface/sc-web || exit 1
    source .venv/bin/activate
    python3 server/app.py
    ;;
  *)
    echo "Usage: $0 {build_kb|machine|web}"  
    exit 1
    ;;
esac
