#!/bin/bash
set -e

NTW_LOG_LEVEL=${NTW_LOG_LEVEL:-1}

COLOR_RESET="\033[0m"
COLOR_BLACK="\033[0;30m"
COLOR_BLUE="\033[0;34m"
COLOR_ORANGE="\033[0;33m"
COLOR_RED="\033[0;31m"

log() {
  if [ ${NTW_LOG_LEVEL} -ge $1 ]; then
    echo -e "${2}[$(date +'%Y-%m-%dT%H:%M:%S%z')] $3${COLOR_RESET}"
  fi
}
debug() {
  log 3 "${COLOR_BLACK}" "DEBUG - $1"
}
info() {
  log 2 "${COLOR_BLUE}" "INFO  - $1"
}
warn() {
  log 1 "${COLOR_ORANGE}" "WARN  - $1"
}
error() {
  log 0 "${COLOR_RED}" "ERROR - $1"
}
info "NTW_LOG_LEVEL: NTW_LOG_LEVEL"

NTW_HOME=${NTW_HOME:-"$HOME/.ntw"}
info "NTW_HOME: $NTW_HOME"

NTW_NODE_DIST_URL=${NTW_NODE_DIST_URL:-"https://nodejs.org/dist"}
info "NTW_NODE_DIST_URL: $NTW_NODE_DIST_URL"

if [ -z $NTW_NPM_URL ]; then
  if [ -f .npmrc ]; then
    npmrcUrl=$(cat .npmrc | grep -E "^registry *= *" | sed -e "s/ //g" | cut -d '=' -f 2)
    if [ -n "$npmrcUrl" ]; then
      debug "Found registry in .npmrc: $npmrcUrl. Using that to download npm packages."
      NTW_NPM_URL=$npmrcUrl
    fi
  fi
fi
if [ -z $NTW_NPM_URL ]; then
  NTW_NPM_URL="https://registry.npmjs.org/"
fi
info "NTW_NPM_URL: $NTW_NPM_URL"

# Usage:
#   selectNode <Version>
# Examples:
#   selectNode v16.13.1
selectNode() {
  debug "selectNode $1 $2 $3"
  debug "PWD: $(pwd)"
  local pwdmd5
  pwdmd5="$(pwd | md5sum | cut -d ' ' -f 1)"
  debug "PWDMD5: $pwdmd5"
  local tars="${NTW_HOME}/tars"
  local home_base="${NTW_HOME}/node/${pwdmd5}"

  local baseUrl=${NTW_NODE_DIST_URL}
  local version=$1
  local os=${2:-$(uname -s | tr '[:upper:]' '[:lower:]')}
  local arch=${3:-$(uname -m | sed -e 's/^aarch64$/arm64/g' | sed -e 's/^x86_64/x64/g')}

  local filename="node-$version-$os-$arch.tar.gz"
  local node_url="${baseUrl}/${version}/node-${version}-${os}-${arch}.tar.gz"
  local sha_url="${baseUrl}/${version}/SHASUMS256.txt"
  local cache_location="${tars}/node-${version}-${os}-${arch}.tar.gz"
  local node_home="${home_base}/node-${version}-${os}-${arch}"

  mkdir -p "$tars"
  mkdir -p "$home_base"

  debug "sha_url: $sha_url"
  local expected_sha
  expected_sha=$(curl -s "$sha_url" 2>/dev/null | grep "$filename" | cut -d " " -f 1)
  debug "expected_sha: $expected_sha"
  local actual_sha

  if [ -f "$cache_location" ]; then
    actual_sha=$(sha256sum "$cache_location" | cut -d " " -f 1)
    debug "actual_sha: $actual_sha"
    if [ "$actual_sha" != "$expected_sha" ]; then
      warn "Cache invalid. Downloading $node_url to $cache_location"
      curl -s "$node_url" -o "$cache_location"
    else
      info "Using cached $filename"
    fi
  else
    info "Tar doesn't exist locally. Downloading $node_url to $cache_location"
    curl -s "$node_url" -o "$cache_location"
  fi

  if [ ! -d "$node_home" ]; then
    info "Extracting tar into $node_home"
    tar xzf "$cache_location" --directory "$home_base"
  fi

  debug "Setting NODE_HOME='$node_home'"
  export NODE_HOME="$node_home"
  export PATH="$NODE_HOME/bin:$PATH"
}

# Usage:
#   selectTool <toolName> <version>
selectTool() {
  debug "selectTool $1 $2"
  local toolName=$1
  local npmUrl=${NTW_NPM_URL}
  if [ -f .npmrc ]; then
    npmrcUrl=$(cat .npmrc | grep -E "^registry *= *" | sed -e "s/ //g" | cut -d '=' -f 2)
    if [ -n "$npmrcUrl" ]; then
      debug "Found registry in .npmrc: $npmrcUrl. Using that to download"
      npmUrl=$npmrcUrl
    fi
  fi
  debug "npmUrl: $npmUrl"
  local version=$2

  if which "${toolName}" >/dev/null 2>&1; then
    debug "Tool ${toolName} already installed. Checking version"
    if [ "$("${toolName}" --version)" = "$version" ]; then
      info "Tool ${toolName} is already at version ${version}"
    else
      warn "Tool ${toolName} is not at version ${version}. Installing ${version}"
      npm install "${toolName}@${version}" --registry="${npmUrl}" --global
    fi
  else
    info "Installing ${toolName} from ${npmUrl}@${version}"
    npm install "${toolName}@${version}" --registry="${npmUrl}" --global
  fi
}

update() {
  info "Updating ${BASH_SOURCE[0]} ..."
  cp "${NTW_HOME}/repo/.ntw.sh" "${BASH_SOURCE[0]}"
  info "... done"
}

checkForUpdate() {
  debug "Checking for update..."
  if [ ! -f "${NTW_HOME}/last-update-check" ]; then
    debug "No last-update-check file found. Setting do_update_cache to 1"
    echo 0 >"${NTW_HOME}/last-update-check"
    do_update_cache=1
  else
    debug "last-update-check file found. Reading"
    last_update_check=$(cat "${NTW_HOME}/last-update-check")
    if [ $(($(date +%s) - $last_update_check)) -gt 604800 ]; then
      debug "last-update-check is older than 7 days. Setting do_update_cache to 1"
      do_update_cache=1
    else
      debug "last-update-check is younger than 7 days. Setting do_update_cache to 0"
      do_update_cache=0
    fi
  fi

  if [ $do_update_cache -eq 1 ]; then
    date +%s >"${NTW_HOME}/last-update-check"
    if [ -d "${NTW_HOME}/repo" ]; then
      (
        cd "${NTW_HOME}/repo"
        git pull
      )
    else
      git clone https://github.com/rahulsom/node-tool-wrapper.git "${NTW_HOME}/repo"
    fi
  fi

  cmp -s "${NTW_HOME}/repo/.ntw.sh" "${BASH_SOURCE[0]}" || warn "Update available for node-tool-wrapper. Run './${BASH_SOURCE[0]} update' to update"
}

if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
  debug "script ${BASH_SOURCE[0]} is top level ..."
  if [ "$1" = "update" ]; then
    update
  fi
else
  debug "script ${BASH_SOURCE[0]} is being sourced ..."
  if [ "$CI" = "" ]; then
    NTW_OFFLINE=1
    checkForUpdate
  fi
  if [ "$NTW_OFFLINE" != "1" ]; then
    checkForUpdate
  fi
fi
