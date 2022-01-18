#!/bin/bash
set -e

NTW_HOME=${NTW_HOME:-"$HOME/.ntw"}
NTW_LOG_LEVEL=${NTW_LOG_LEVEL:-1}
NTW_NODE_DIST_URL=${NTW_NODE_DIST_URL:-"https://nodejs.org/dist"}
NTW_NPM_URL=${NTW_NPM_URL:-"https://registry.npmjs.org/"}

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

debug "NTW_HOME: $NTW_HOME"
debug "NTW_NODE_DIST_URL: $NTW_NODE_DIST_URL"
debug "NTW_NPM_URL: $NTW_NPM_URL"

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
  local arch=${3:-$(uname -m | sed -e 's/^aarch64$/arm64/g')}

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
}

checkForUpdate() {
  debug "Checking for update..."
}

if [[ "${BASH_SOURCE[0]}" = "${0}" ]]; then
  debug "script ${BASH_SOURCE[0]} is top level ..."
  update
else
  debug "script ${BASH_SOURCE[0]} is being sourced ..."
  checkForUpdate
fi
